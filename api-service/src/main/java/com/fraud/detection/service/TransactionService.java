package com.fraud.detection.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fraud.detection.dto.MlScoreRequest;
import com.fraud.detection.dto.MlScoreResponse;
import com.fraud.detection.dto.TransactionRequest;
import com.fraud.detection.dto.TransactionResponse;
import com.fraud.detection.entity.*;
import com.fraud.detection.repository.FraudAssessmentRepository;
import com.fraud.detection.repository.ReviewCaseRepository;
import com.fraud.detection.repository.TransactionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class TransactionService {

    private final TransactionRepository transactionRepository;
    private final FraudAssessmentRepository fraudAssessmentRepository;
    private final ReviewCaseRepository reviewCaseRepository;
    private final MlClientService mlClientService;
    private final ObjectMapper objectMapper;

    @Value("${fraud.threshold.low:0.30}")
    private double lowThreshold;

    @Value("${fraud.threshold.high:0.85}")
    private double highThreshold;

    @Transactional
    public TransactionResponse processTransaction(TransactionRequest request) {
        log.info("Processing incoming transaction ref: {}, amount: {}", request.getTransactionRef(), request.getAmount());

        // 1. Map to ML Scoring payload
        MlScoreRequest scoreRequest = MlScoreRequest.builder()
                .transactionRef(request.getTransactionRef())
                .transactionAmt(request.getAmount())
                .productCd(request.getProductCd())
                .card1(request.getCard1())
                .card2(request.getCard2())
                .card3(request.getCard3())
                .card4(request.getCard4())
                .card5(request.getCard5())
                .card6(request.getCard6())
                .addr1(request.getAddr1())
                .addr2(request.getAddr2())
                .dist1(request.getDist1())
                .dist2(request.getDist2())
                .pEmailDomain(request.getPEmailDomain())
                .rEmailDomain(request.getREmailDomain())
                .deviceType(request.getDeviceType())
                .deviceInfo(request.getDeviceInfo())
                .browserVersion(request.getBrowserVersion())
                .additionalFeatures(request.getAdditionalFeatures())
                .build();

        // 2. Call ML Service scoring endpoint
        MlScoreResponse scoreResponse = mlClientService.scoreTransaction(scoreRequest);
        BigDecimal prob = scoreResponse.getFraudProbability();
        double probValue = prob != null ? prob.doubleValue() : 0.0;

        // 3. Apply business decision threshold
        DecisionStatus decision;
        if (probValue < lowThreshold) {
            decision = DecisionStatus.APPROVE;
        } else if (probValue >= highThreshold) {
            decision = DecisionStatus.BLOCK;
        } else {
            decision = DecisionStatus.FLAGGED;
        }

        // 4. Persist or update Transaction (Idempotent upsert)
        TransactionEntity transaction = transactionRepository.findByTransactionRef(request.getTransactionRef())
                .orElse(null);

        if (transaction != null) {
            transaction.setUserId(request.getUserId());
            transaction.setAmount(request.getAmount());
            transaction.setCurrency(request.getCurrency() != null ? request.getCurrency() : "USD");
            transaction.setProductCd(request.getProductCd());
            transaction.setCard1(request.getCard1());
            transaction.setCard2(request.getCard2());
            transaction.setCard3(request.getCard3());
            transaction.setCard4(request.getCard4());
            transaction.setCard5(request.getCard5());
            transaction.setCard6(request.getCard6());
            transaction.setPEmailDomain(request.getPEmailDomain());
            transaction.setREmailDomain(request.getREmailDomain());
            transaction.setDeviceType(request.getDeviceType());
            transaction.setDeviceInfo(request.getDeviceInfo());
            transaction.setStatus(decision);
        } else {
            transaction = TransactionEntity.builder()
                    .transactionRef(request.getTransactionRef())
                    .userId(request.getUserId())
                    .amount(request.getAmount())
                    .currency(request.getCurrency() != null ? request.getCurrency() : "USD")
                    .productCd(request.getProductCd())
                    .card1(request.getCard1())
                    .card2(request.getCard2())
                    .card3(request.getCard3())
                    .card4(request.getCard4())
                    .card5(request.getCard5())
                    .card6(request.getCard6())
                    .pEmailDomain(request.getPEmailDomain())
                    .rEmailDomain(request.getREmailDomain())
                    .deviceType(request.getDeviceType())
                    .deviceInfo(request.getDeviceInfo())
                    .status(decision)
                    .build();
        }

        transaction = transactionRepository.save(transaction);

        // 5. Persist or update Fraud Assessment
        String riskFactorsJson = null;
        try {
            riskFactorsJson = objectMapper.writeValueAsString(scoreResponse.getRiskFactors());
        } catch (JsonProcessingException e) {
            log.warn("Could not serialize risk factors to JSON: {}", e.getMessage());
        }

        FraudAssessmentEntity assessment = fraudAssessmentRepository.findByTransactionId(transaction.getId())
                .orElse(null);

        if (assessment != null) {
            assessment.setFraudProbability(prob);
            assessment.setDecision(decision);
            assessment.setRiskLevel(scoreResponse.getRiskLevel() != null ? scoreResponse.getRiskLevel() : "MEDIUM");
            assessment.setModelVersion(scoreResponse.getModelVersion() != null ? scoreResponse.getModelVersion() : "v1.0.0-trained");
            assessment.setRiskFactors(riskFactorsJson);
        } else {
            assessment = FraudAssessmentEntity.builder()
                    .transaction(transaction)
                    .fraudProbability(prob)
                    .decision(decision)
                    .riskLevel(scoreResponse.getRiskLevel() != null ? scoreResponse.getRiskLevel() : "MEDIUM")
                    .modelVersion(scoreResponse.getModelVersion() != null ? scoreResponse.getModelVersion() : "v1.0.0-trained")
                    .riskFactors(riskFactorsJson)
                    .build();
        }

        assessment = fraudAssessmentRepository.save(assessment);
        transaction.setAssessment(assessment);

        // 6. If FLAGGED, create or update human review case
        ReviewCaseEntity reviewCase = reviewCaseRepository.findByTransactionId(transaction.getId()).orElse(null);
        if (decision == DecisionStatus.FLAGGED) {
            if (reviewCase == null) {
                reviewCase = ReviewCaseEntity.builder()
                        .transaction(transaction)
                        .reviewStatus(ReviewStatus.PENDING)
                        .analystNotes("Flagged automatically due to risk score between " + lowThreshold + " and " + highThreshold)
                        .build();
                reviewCase = reviewCaseRepository.save(reviewCase);
            }
            transaction.setReviewCase(reviewCase);
        } else if (reviewCase != null) {
            transaction.setReviewCase(reviewCase);
        }

        log.info("Transaction {} completed with decision: {}", transaction.getTransactionRef(), decision);
        return mapToResponse(transaction, assessment, reviewCase);
    }

    @Transactional(readOnly = true)
    public List<TransactionResponse> getTransactions(DecisionStatus status) {
        List<TransactionEntity> transactions;
        if (status != null) {
            transactions = transactionRepository.findByStatusOrderByCreatedAtDesc(status);
        } else {
            transactions = transactionRepository.findAllByOrderByCreatedAtDesc();
        }

        return transactions.stream()
                .map(t -> mapToResponse(t, t.getAssessment(), t.getReviewCase()))
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public TransactionResponse getTransactionById(UUID id) {
        TransactionEntity entity = transactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found with ID: " + id));
        return mapToResponse(entity, entity.getAssessment(), entity.getReviewCase());
    }

    public TransactionResponse mapToResponse(
            TransactionEntity t,
            FraudAssessmentEntity a,
            ReviewCaseEntity r
    ) {
        TransactionResponse.TransactionResponseBuilder builder = TransactionResponse.builder()
                .id(t.getId())
                .transactionRef(t.getTransactionRef())
                .userId(t.getUserId())
                .amount(t.getAmount())
                .currency(t.getCurrency())
                .productCd(t.getProductCd())
                .card4(t.getCard4())
                .card6(t.getCard6())
                .pEmailDomain(t.getPEmailDomain())
                .rEmailDomain(t.getREmailDomain())
                .deviceType(t.getDeviceType())
                .deviceInfo(t.getDeviceInfo())
                .status(t.getStatus())
                .createdAt(t.getCreatedAt());

        if (a != null) {
            builder.fraudProbability(a.getFraudProbability())
                    .riskLevel(a.getRiskLevel())
                    .modelVersion(a.getModelVersion())
                    .riskFactorsJson(a.getRiskFactors());
        }

        if (r != null) {
            builder.reviewCaseId(r.getId())
                    .reviewStatus(r.getReviewStatus())
                    .analystId(r.getAnalystId())
                    .analystNotes(r.getAnalystNotes())
                    .resolvedAt(r.getResolvedAt());
        }

        return builder.build();
    }
}
