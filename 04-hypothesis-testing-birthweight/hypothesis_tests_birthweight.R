# =============================================================
# Project 4: Maternal Risk Factors and Birth Weight
#            Hypothesis Testing and Statistical Inference
# Dataset : Baystate Medical Center births, 1986 (Hosmer and Lemeshow), n = 189
# Author  : Princess Ijeoma Agudosi
# Tools   : R (base stats, car, ggplot2, dplyr)
# =============================================================

library(dplyr)
library(ggplot2)
library(car)

options(scipen = 999)
theme_set(theme_minimal(base_size = 12))
dir.create("figures", showWarnings = FALSE)
dir.create("output", showWarnings = FALSE)
alpha <- 0.05

# ---- 1. Load and label ----------------------------------------
bw <- read.csv("data/birthwt.csv")
bw$rownames <- NULL
bw <- bw %>% mutate(
  smoke_f = factor(smoke, 0:1, c("Non-smoker", "Smoker")),
  low_f   = factor(low,   0:1, c("Normal weight", "Low birth weight")),
  race_f  = factor(race,  1:3, c("White", "Black", "Other")),
  ht_f    = factor(ht,    0:1, c("No hypertension", "Hypertension")),
  ptl_any = factor(ptl > 0, c(FALSE, TRUE), c("No previous preterm", "Previous preterm"))
)
str(bw); cat("Missing values:", sum(is.na(bw)), "\n")

desc <- bw %>% group_by(smoke_f) %>%
  summarise(n = n(), mean_bwt = mean(bwt), sd_bwt = sd(bwt),
            median_bwt = median(bwt), pct_low = 100 * mean(low))
print(desc)
write.csv(desc, "output/descriptives_by_smoking.csv", row.names = FALSE)

# ---- 2. H1: Mean birth weight differs by smoking -------------
# H0: mu_smoker = mu_nonsmoker ; H1: mu_smoker != mu_nonsmoker
cat("\n== H1: birth weight by smoking status ==\n")
print(by(bw$bwt, bw$smoke_f, function(x) shapiro.test(x)))   # normality per group
print(leveneTest(bwt ~ smoke_f, data = bw, center = mean))   # equal variances
t1 <- t.test(bwt ~ smoke_f, data = bw, var.equal = FALSE)    # Welch t-test
print(t1)
m  <- tapply(bw$bwt, bw$smoke_f, mean); s <- tapply(bw$bwt, bw$smoke_f, sd)
nn <- table(bw$smoke_f)
sp <- sqrt(((nn[1] - 1) * s[1]^2 + (nn[2] - 1) * s[2]^2) / (sum(nn) - 2))
d  <- unname((m[1] - m[2]) / sp)
cat(sprintf("Cohen's d = %.2f\n", d))
print(wilcox.test(bwt ~ smoke_f, data = bw, exact = FALSE))   # non-parametric check
print(power.t.test(n = min(nn), delta = abs(m[1] - m[2]), sd = sp, sig.level = alpha))

p1 <- ggplot(bw, aes(smoke_f, bwt, fill = smoke_f)) +
  geom_violin(alpha = 0.4, colour = NA) +
  geom_boxplot(width = 0.25, outlier.shape = NA) +
  geom_jitter(width = 0.08, alpha = 0.35, size = 1.2) +
  geom_hline(yintercept = 2500, linetype = "dashed", colour = "#c1121f") +
  scale_fill_manual(values = c("#2a6f97", "#c1121f"), guide = "none") +
  labs(title = "Birth weight by maternal smoking during pregnancy",
       subtitle = "Dashed line marks the low birth weight threshold (2,500 g)",
       x = NULL, y = "Birth weight (grams)")
ggsave("figures/01_bwt_by_smoking.png", p1, width = 7, height = 5, dpi = 150)

# ---- 3. H2: Low birth weight is associated with smoking ------
# H0: smoking and low birth weight are independent
cat("\n== H2: low birth weight by smoking (chi-square) ==\n")
tab <- table(bw$smoke_f, bw$low_f); print(addmargins(tab))
print(round(prop.table(tab, 1) * 100, 1))
chi <- chisq.test(tab, correct = FALSE); print(chi); print(chi$expected)
print(chisq.test(tab))                                    # Yates-corrected
p_s <- tab["Smoker", 2] / sum(tab["Smoker", ]); p_n <- tab["Non-smoker", 2] / sum(tab["Non-smoker", ])
rr  <- p_s / p_n
se_lrr <- sqrt(1 / tab["Smoker", 2] - 1 / sum(tab["Smoker", ]) +
               1 / tab["Non-smoker", 2] - 1 / sum(tab["Non-smoker", ]))
cat(sprintf("Risk: smokers %.1f%%, non-smokers %.1f%% | Risk difference = %.1f points\n",
            100 * p_s, 100 * p_n, 100 * (p_s - p_n)))
cat(sprintf("Relative risk = %.2f (95%% CI %.2f to %.2f)\n",
            rr, exp(log(rr) - 1.96 * se_lrr), exp(log(rr) + 1.96 * se_lrr)))
print(fisher.test(tab))                                   # exact odds ratio and CI
print(prop.test(tab[, 2], rowSums(tab), correct = FALSE)) # CI for difference in proportions

# ---- 4. H3: Birth weight differs by race (one-way ANOVA) -----
cat("\n== H3: birth weight by race ==\n")
print(bw %>% group_by(race_f) %>% summarise(n = n(), mean = mean(bwt), sd = sd(bwt)))
print(leveneTest(bwt ~ race_f, data = bw, center = mean))
a3 <- aov(bwt ~ race_f, data = bw); print(summary(a3))
ss <- summary(a3)[[1]][["Sum Sq"]]; cat(sprintf("Eta squared = %.3f\n", ss[1] / sum(ss)))
print(TukeyHSD(a3))
print(kruskal.test(bwt ~ race_f, data = bw))
shapiro.test(residuals(a3))

# ---- 5. H4: Hypertension and previous preterm labour ---------
cat("\n== H4: other clinical risk factors ==\n")
for (v in c("ht_f", "ptl_any")) {
  cat("\n--", v, "--\n")
  print(bw %>% group_by(.data[[v]]) %>% summarise(n = n(), mean = mean(bwt), pct_low = 100 * mean(low)))
  print(t.test(bw$bwt ~ bw[[v]], var.equal = FALSE))
  print(fisher.test(table(bw[[v]], bw$low_f)))            # small cells, so exact test
}

# ---- 6. H5: Mother's weight is correlated with birth weight --
cat("\n== H5: correlation between mother's weight and birth weight ==\n")
print(cor.test(bw$lwt, bw$bwt, method = "pearson"))
print(cor.test(bw$lwt, bw$bwt, method = "spearman", exact = FALSE))
print(cor.test(bw$age, bw$bwt, method = "pearson"))

# ---- 7. Multiple testing correction --------------------------
pvals <- c(
  H1_ttest_smoking   = t1$p.value,
  H2_chisq_smoking   = chi$p.value,
  H3_anova_race      = summary(a3)[[1]][["Pr(>F)"]][1],
  H4a_ttest_hyperten = t.test(bwt ~ ht_f, data = bw)$p.value,
  H4b_ttest_preterm  = t.test(bwt ~ ptl_any, data = bw)$p.value,
  H5_cor_motherwt    = cor.test(bw$lwt, bw$bwt)$p.value,
  H5b_cor_age        = cor.test(bw$age, bw$bwt)$p.value
)
adj <- data.frame(test = names(pvals), p_raw = round(pvals, 4),
                  p_holm = round(p.adjust(pvals, "holm"), 4),
                  p_BH = round(p.adjust(pvals, "BH"), 4))
print(adj)
write.csv(adj, "output/p_values_adjusted.csv", row.names = FALSE)

# ---- 8. Does smoking still matter after adjustment? ----------
cat("\n== Adjusted analysis: logistic regression for low birth weight ==\n")
lg <- glm(low ~ smoke_f + race_f + lwt + age + ht_f + ptl_any + factor(ui),
          family = binomial, data = bw)
print(summary(lg))
or <- exp(cbind(OR = coef(lg), confint.default(lg)))
print(round(or, 3))
write.csv(round(or, 3), "output/adjusted_odds_ratios.csv")

p2 <- bw %>% group_by(race_f, smoke_f) %>% summarise(pct_low = 100 * mean(low), n = n(), .groups = "drop") %>%
  ggplot(aes(race_f, pct_low, fill = smoke_f)) +
  geom_col(position = position_dodge(0.8), width = 0.7) +
  geom_text(aes(label = paste0("n=", n)), position = position_dodge(0.8), vjust = -0.4, size = 3.3) +
  scale_fill_manual(values = c("#2a6f97", "#c1121f")) +
  labs(title = "Percentage of low birth weight babies by race and smoking",
       x = "Mother's race", y = "Low birth weight (%)", fill = NULL)
ggsave("figures/02_low_bwt_race_smoking.png", p2, width = 8, height = 5, dpi = 150)

p3 <- ggplot(bw, aes(lwt, bwt, colour = smoke_f)) +
  geom_point(alpha = 0.6) + geom_smooth(method = "lm", se = FALSE) +
  scale_colour_manual(values = c("#2a6f97", "#c1121f")) +
  labs(title = "Mother's weight and birth weight",
       x = "Mother's weight at last menstrual period (lb)", y = "Birth weight (grams)", colour = NULL)
ggsave("figures/03_motherwt_bwt.png", p3, width = 8, height = 5, dpi = 150)

sessionInfo()
