package com.fraud.detection.dto;

import com.fraud.detection.entity.ReviewStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ReviewDecisionRequest {

    @NotBlank(message = "analystId is required")
    private String analystId;

    @NotNull(message = "reviewStatus is required (CONFIRMED_FRAUD or FALSE_POSITIVE)")
    private ReviewStatus reviewStatus;

    private String analystNotes;
}
