package com.fraud.detection.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "transactions")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TransactionEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "transaction_ref", unique = true, nullable = false, length = 64)
    private String transactionRef;

    @Column(name = "user_id", nullable = false, length = 64)
    private String userId;

    @Column(name = "amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal amount;

    @Column(name = "currency", nullable = false, length = 3)
    private String currency;

    @Column(name = "product_cd", nullable = false, length = 10)
    private String productCd;

    @Column(name = "card1", length = 32)
    private String card1;

    @Column(name = "card2", length = 32)
    private String card2;

    @Column(name = "card3", length = 32)
    private String card3;

    @Column(name = "card4", length = 32)
    private String card4;

    @Column(name = "card5", length = 32)
    private String card5;

    @Column(name = "card6", length = 32)
    private String card6;

    @Column(name = "p_emaildomain", length = 100)
    private String pEmailDomain;

    @Column(name = "r_emaildomain", length = 100)
    private String rEmailDomain;

    @Column(name = "device_type", length = 50)
    private String deviceType;

    @Column(name = "device_info", length = 150)
    private String deviceInfo;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    private DecisionStatus status;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    @Builder.Default
    private Instant createdAt = Instant.now();

    @OneToOne(mappedBy = "transaction", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private FraudAssessmentEntity assessment;

    @OneToOne(mappedBy = "transaction", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private ReviewCaseEntity reviewCase;
}
