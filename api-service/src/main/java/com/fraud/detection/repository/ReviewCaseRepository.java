package com.fraud.detection.repository;

import com.fraud.detection.entity.ReviewCaseEntity;
import com.fraud.detection.entity.ReviewStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ReviewCaseRepository extends JpaRepository<ReviewCaseEntity, UUID> {

    Optional<ReviewCaseEntity> findByTransactionId(UUID transactionId);

    List<ReviewCaseEntity> findByReviewStatusOrderByCreatedAtDesc(ReviewStatus reviewStatus);

    @Query("SELECT COUNT(r) FROM ReviewCaseEntity r WHERE r.reviewStatus = :status")
    long countByReviewStatus(ReviewStatus status);
}
