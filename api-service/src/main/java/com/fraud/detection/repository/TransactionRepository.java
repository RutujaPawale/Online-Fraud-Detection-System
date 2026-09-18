package com.fraud.detection.repository;

import com.fraud.detection.entity.DecisionStatus;
import com.fraud.detection.entity.TransactionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface TransactionRepository extends JpaRepository<TransactionEntity, UUID> {

    Optional<TransactionEntity> findByTransactionRef(String transactionRef);

    List<TransactionEntity> findAllByOrderByCreatedAtDesc();

    List<TransactionEntity> findByStatusOrderByCreatedAtDesc(DecisionStatus status);

    @Query("SELECT COUNT(t) FROM TransactionEntity t WHERE t.status = :status")
    long countByStatus(DecisionStatus status);
}
