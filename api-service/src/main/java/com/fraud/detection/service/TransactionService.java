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

        // 4. Persist Transaction
        TransactionEntity transaction = TransactionEntity.builder()
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

        transaction = transactionRepository.save(transaction);

        // 5. Persist Fraud Assessment
        String riskFactorsJson = null;
        try {
            riskFactorsJson = objectMapper.writeValueAsString(scoreResponse.getRiskFactors());
        } catch (JsonProcessingException e) {
            log.warn("Could not serialize risk factors to JSON: {}", e.getMessage());
        }

        FraudAssessmentEntity assessment = FraudAssessmentEntity.builder()
                .transaction(transaction)
                .fraudProbability(prob)
                .decision(decision)
                .riskLevel(scoreResponse.getRiskLevel() != null ? scoreResponse.getRiskLevel() : "MEDIUM")
                .modelVersion(scoreResponse.getModelVersion() != null ? scoreResponse.getModelVersion() : "v0.1.0")
                .riskFactors(riskFactorsJson)
                .build();

        assessment = fraudAssessmentRepository.save(assessment);
        transaction.setAssessment(assessment);

        // 6. If FLAGGED, create human review case
        ReviewCaseEntity reviewCase = null;
        if (decision == DecisionStatus.FLAGGED) {
            reviewCase = ReviewCaseEntity.builder()
                    .transaction(transaction)
                    .reviewStatus(ReviewStatus.PENDING)
                    .analystNotes("Flagged automatically due to risk score between " + lowThreshold + " and " + highThreshold)
                    .build();
            reviewCase = reviewCaseRepository.save(reviewCase);
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
