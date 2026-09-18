package com.fraud.detection.repository;

import com.fraud.detection.entity.FraudAssessmentEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface FraudAssessmentRepository extends JpaRepository<FraudAssessmentEntity, UUID> {
    Optional<FraudAssessmentEntity> findByTransactionId(UUID transactionId);
}
