package com.fraud.detection.controller;

import com.fraud.detection.dto.ReviewDecisionRequest;
import com.fraud.detection.dto.TransactionResponse;
import com.fraud.detection.service.ReviewService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/reviews")
@RequiredArgsConstructor
public class ReviewController {

    private final ReviewService reviewService;

    @GetMapping("/flagged")
    public ResponseEntity<List<TransactionResponse>> getPendingReviews() {
        List<TransactionResponse> pending = reviewService.getPendingReviews();
        return ResponseEntity.ok(pending);
    }

    @PatchMapping("/transactions/{transactionId}")
    public ResponseEntity<TransactionResponse> submitReview(
            @PathVariable UUID transactionId,
            @Valid @RequestBody ReviewDecisionRequest request
    ) {
        TransactionResponse updated = reviewService.reviewTransaction(transactionId, request);
        return ResponseEntity.ok(updated);
    }
}
