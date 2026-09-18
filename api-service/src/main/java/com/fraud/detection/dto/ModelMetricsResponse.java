package com.fraud.detection.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

import java.time.Instant;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ModelMetricsResponse {

    @JsonProperty("model_name")
    private String modelName;

    @JsonProperty("model_version")
    private String modelVersion;

    @JsonProperty("imbalance_handling")
    private String imbalanceHandling;

    @JsonProperty("evaluation_dataset")
    private String evaluationDataset;

    private Double precision;
    private Double recall;

    @JsonProperty("f1_score")
    private Double f1Score;

    @JsonProperty("auc_pr")
    private Double aucPr;

    @JsonProperty("roc_auc")
    private Double rocAuc;

    @JsonProperty("optimal_threshold")
    private Double optimalThreshold;

    @JsonProperty("confusion_matrix")
    private ConfusionMatrixDto confusionMatrix;

    @JsonProperty("evaluated_at")
    private Instant evaluatedAt;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class ConfusionMatrixDto {
        @JsonProperty("true_negatives")
        private Long trueNegatives;

        @JsonProperty("false_positives")
        private Long falsePositives;

        @JsonProperty("false_negatives")
        private Long falseNegatives;

        @JsonProperty("true_positives")
        private Long truePositives;
    }
}
