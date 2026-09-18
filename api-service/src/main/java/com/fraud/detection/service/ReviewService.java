package com.fraud.detection.service;

import com.fraud.detection.dto.ReviewDecisionRequest;
import com.fraud.detection.dto.TransactionResponse;
import com.fraud.detection.entity.DecisionStatus;
import com.fraud.detection.entity.ReviewCaseEntity;
import com.fraud.detection.entity.ReviewStatus;
import com.fraud.detection.entity.TransactionEntity;
import com.fraud.detection.repository.ReviewCaseRepository;
import com.fraud.detection.repository.TransactionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ReviewService {

    private final ReviewCaseRepository reviewCaseRepository;
    private final TransactionRepository transactionRepository;
    private final TransactionService transactionService;

    @Transactional
    public TransactionResponse reviewTransaction(UUID transactionId, ReviewDecisionRequest request) {
        log.info("Analyst {} reviewing transaction ID: {} with decision: {}",
                request.getAnalystId(), transactionId, request.getReviewStatus());

        final TransactionEntity transaction = transactionRepository.findById(transactionId)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found with ID: " + transactionId));

        ReviewCaseEntity reviewCase = reviewCaseRepository.findByTransactionId(transactionId)
                .orElseGet(() -> ReviewCaseEntity.builder()
                        .transaction(transaction)
                        .build());

        reviewCase.setAnalystId(request.getAnalystId());
        reviewCase.setReviewStatus(request.getReviewStatus());
        reviewCase.setAnalystNotes(request.getAnalystNotes());
        reviewCase.setResolvedAt(Instant.now());

        // Update transaction status based on human review
        if (request.getReviewStatus() == ReviewStatus.CONFIRMED_FRAUD) {
            transaction.setStatus(DecisionStatus.BLOCK);
        } else if (request.getReviewStatus() == ReviewStatus.FALSE_POSITIVE) {
            transaction.setStatus(DecisionStatus.APPROVE);
        }

        reviewCaseRepository.save(reviewCase);
        TransactionEntity savedTransaction = transactionRepository.save(transaction);

        return transactionService.mapToResponse(savedTransaction, savedTransaction.getAssessment(), reviewCase);
    }

    @Transactional(readOnly = true)
    public List<TransactionResponse> getPendingReviews() {
        return reviewCaseRepository.findByReviewStatusOrderByCreatedAtDesc(ReviewStatus.PENDING)
                .stream()
                .map(rc -> transactionService.mapToResponse(rc.getTransaction(), rc.getTransaction().getAssessment(), rc))
                .collect(Collectors.toList());
    }
}
