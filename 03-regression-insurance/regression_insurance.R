# =============================================================
# Project 3: Modelling Medical Insurance Charges with Regression
# Dataset : Medical Cost Personal Dataset (n = 1,338)
# Author  : Princess Ijeoma Agudosi
# Tools   : R (ggplot2, dplyr, car, broom)
# =============================================================

library(dplyr)
library(ggplot2)
library(car)
library(broom)

options(scipen = 999)
theme_set(theme_minimal(base_size = 12))
dir.create("figures", showWarnings = FALSE)
dir.create("output", showWarnings = FALSE)
set.seed(2026)

# ---- 1. Load, check, prepare ---------------------------------
ins <- read.csv("data/insurance.csv", stringsAsFactors = TRUE)
str(ins); cat("\nMissing:", sum(is.na(ins)), "| Duplicate rows:", sum(duplicated(ins)), "\n")
ins <- distinct(ins)                       # drop the single duplicated record
ins$smoker <- relevel(ins$smoker, ref = "no")
ins$sex    <- relevel(ins$sex, ref = "female")
ins$region <- relevel(ins$region, ref = "northeast")
ins$obese  <- factor(ifelse(ins$bmi >= 30, "yes", "no"), levels = c("no", "yes"))
summary(ins)

# ---- 2. Exploratory checks -----------------------------------
cat("\nMean charges by smoker status:\n")
print(ins %>% group_by(smoker) %>% summarise(n = n(), mean = mean(charges), median = median(charges)))
cat("\nSkewness indicator: mean =", round(mean(ins$charges)),
    " median =", round(median(ins$charges)), "\n")

p1 <- ggplot(ins, aes(charges)) +
  geom_histogram(bins = 40, fill = "#2a6f97", colour = "white") +
  labs(title = "Distribution of annual medical charges",
       subtitle = "Strong right skew motivates a log transformation",
       x = "Charges (US$)", y = "Count")
ggsave("figures/01_charges_hist.png", p1, width = 8, height = 5, dpi = 150)

p2 <- ggplot(ins, aes(bmi, charges, colour = smoker)) +
  geom_point(alpha = 0.55) +
  geom_smooth(method = "lm", se = FALSE) +
  geom_vline(xintercept = 30, linetype = "dashed", colour = "grey40") +
  scale_colour_manual(values = c(no = "#2a6f97", yes = "#c1121f")) +
  labs(title = "BMI raises charges sharply for smokers only",
       subtitle = "Dashed line marks the obesity threshold (BMI 30)",
       x = "Body mass index", y = "Charges (US$)", colour = "Smoker")
ggsave("figures/02_bmi_smoker_interaction.png", p2, width = 8, height = 5, dpi = 150)

p3 <- ggplot(ins, aes(age, charges, colour = interaction(smoker, obese, sep = " / "))) +
  geom_point(alpha = 0.6) +
  labs(title = "Charges rise with age in three distinct bands",
       x = "Age", y = "Charges (US$)", colour = "Smoker / Obese")
ggsave("figures/03_age_bands.png", p3, width = 8, height = 5, dpi = 150)

# ---- 3. Train / test split -----------------------------------
idx   <- sample(seq_len(nrow(ins)), size = round(0.8 * nrow(ins)))
train <- ins[idx, ]; test <- ins[-idx, ]
cat("\nTraining rows:", nrow(train), "| Test rows:", nrow(test), "\n")

# ---- 4. Candidate models -------------------------------------
m1 <- lm(charges ~ age + sex + bmi + children + smoker + region, data = train)
m2 <- lm(log(charges) ~ age + sex + bmi + children + smoker + region, data = train)
m3 <- lm(charges ~ age + I(age^2) + sex + bmi + children + region + smoker * obese, data = train)

for (nm in c("m1", "m2", "m3")) {
  cat("\n================", nm, "================\n"); print(summary(get(nm)))
}

# Model comparison on the training data
comp <- data.frame(
  model = c("M1: linear, all main effects",
            "M2: log(charges), all main effects",
            "M3: age^2 + smoker x obese interaction"),
  adj_r2 = c(summary(m1)$adj.r.squared, summary(m2)$adj.r.squared, summary(m3)$adj.r.squared),
  AIC    = c(AIC(m1), NA, AIC(m3))   # AIC not comparable for a log outcome
)

# ---- 5. Diagnostics for the chosen model (M3) ----------------
cat("\nVariance inflation factors (M3, main effects model used for VIF):\n")
print(vif(lm(charges ~ age + sex + bmi + children + region + smoker + obese, data = train)))

png("figures/04_diagnostics_m3.png", width = 1400, height = 1100, res = 150)
par(mfrow = c(2, 2)); plot(m3); dev.off()
png("figures/05_diagnostics_m1.png", width = 1400, height = 1100, res = 150)
par(mfrow = c(2, 2)); plot(m1); dev.off()

cooks <- cooks.distance(m3)
cat("\nObservations with Cook's distance > 4/n:", sum(cooks > 4 / nrow(train)), "\n")
cat("Largest Cook's distance:", round(max(cooks), 4), "\n")
print(ncvTest(m3))       # Breusch-Pagan style test for non-constant variance

# Robust (HC3) standard errors as a check on inference under heteroscedasticity
robust_se <- sqrt(diag(hccm(m3, type = "hc3")))
robust <- data.frame(term = names(coef(m3)), estimate = coef(m3),
                     se_ols = summary(m3)$coef[, 2], se_hc3 = robust_se)
print(robust, digits = 4)

# ---- 6. Out-of-sample performance ----------------------------
rmse <- function(a, p) sqrt(mean((a - p)^2))
mae  <- function(a, p) mean(abs(a - p))
smear <- mean(exp(residuals(m2)))                 # Duan smearing for log model
pred <- list(M1 = predict(m1, test),
             M2 = exp(predict(m2, test)) * smear,
             M3 = predict(m3, test))
perf <- data.frame(model = names(pred),
                   test_RMSE = sapply(pred, function(p) rmse(test$charges, p)),
                   test_MAE  = sapply(pred, function(p) mae(test$charges, p)),
                   test_R2   = sapply(pred, function(p) cor(test$charges, p)^2))
comp <- cbind(comp, perf[, -1])
print(comp, digits = 4)
write.csv(comp, "output/model_comparison.csv", row.names = FALSE)

# ---- 7. Final model on all data, tidy output -----------------
final <- lm(charges ~ age + I(age^2) + sex + bmi + children + region + smoker * obese, data = ins)
print(summary(final))
coefs <- tidy(final, conf.int = TRUE)
print(coefs, n = 20)
write.csv(coefs, "output/final_model_coefficients.csv", row.names = FALSE)
glance(final)

pd <- data.frame(actual = test$charges, predicted = pred$M3)
p6 <- ggplot(pd, aes(actual, predicted)) +
  geom_point(alpha = 0.6, colour = "#2a6f97") +
  geom_abline(linetype = "dashed") +
  labs(title = "Final model: predicted vs actual charges (test set)",
       x = "Actual charges (US$)", y = "Predicted charges (US$)")
ggsave("figures/06_pred_vs_actual.png", p6, width = 7, height = 6, dpi = 150)

# Worked example: predicted charges for a 40-year-old, BMI 32, 1 child, southeast
ex <- expand.grid(age = 40, sex = factor("female", levels = levels(ins$sex)), bmi = 32,
                  children = 1, region = factor("southeast", levels = levels(ins$region)),
                  smoker = factor(c("no", "yes"), levels = levels(ins$smoker)))
ex$obese <- factor("yes", levels = c("no", "yes"))
ex$predicted <- predict(final, ex)
print(ex)

sessionInfo()
