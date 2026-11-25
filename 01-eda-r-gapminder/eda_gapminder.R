# =============================================================
# Project 1: Exploratory Data Analysis of Global Development
# Dataset : Gapminder (142 countries, 1952 to 2007)
# Author  : Princess Ijeoma Agudosi
# Tools   : R (dplyr, tidyr, ggplot2, scales)
# =============================================================

library(dplyr)
library(tidyr)
library(ggplot2)
library(scales)

options(scipen = 999)
theme_set(theme_minimal(base_size = 12))
dir.create("figures", showWarnings = FALSE)
dir.create("output", showWarnings = FALSE)

# ---- 1. Load and inspect -------------------------------------
gap <- read.csv("data/gapminder.csv", stringsAsFactors = FALSE)
gap$rownames <- NULL

str(gap)
cat("\nMissing values per column:\n"); print(colSums(is.na(gap)))
cat("\nCountries:", n_distinct(gap$country),
    " | Years:", paste(range(gap$year), collapse = " to "),
    " | Rows:", nrow(gap), "\n")

# ---- 2. Summary statistics -----------------------------------
overall <- gap %>%
  summarise(across(c(lifeExp, gdpPercap, pop),
                   list(mean = mean, median = median, sd = sd,
                        min = min, max = max)))
print(t(round(overall, 2)))

by_continent_2007 <- gap %>%
  filter(year == 2007) %>%
  group_by(continent) %>%
  summarise(countries      = n(),
            median_lifeExp = round(median(lifeExp), 1),
            mean_lifeExp   = round(mean(lifeExp), 1),
            sd_lifeExp     = round(sd(lifeExp), 1),
            median_gdp     = round(median(gdpPercap)),
            .groups = "drop") %>%
  arrange(desc(median_lifeExp))
print(by_continent_2007)
write.csv(by_continent_2007, "output/continent_summary_2007.csv", row.names = FALSE)

# ---- 3. Distributions ----------------------------------------
p1 <- ggplot(filter(gap, year == 2007), aes(lifeExp)) +
  geom_histogram(binwidth = 2.5, fill = "#2a6f97", colour = "white") +
  labs(title = "Distribution of life expectancy, 2007",
       subtitle = "The distribution is left-skewed with a long tail of low values",
       x = "Life expectancy (years)", y = "Number of countries")
ggsave("figures/01_lifeexp_hist_2007.png", p1, width = 8, height = 5, dpi = 150)

p2 <- ggplot(filter(gap, year == 2007),
             aes(reorder(continent, lifeExp, median), lifeExp)) +
  geom_boxplot(fill = "#a9d6e5", outlier.colour = "#c1121f") +
  coord_flip() +
  labs(title = "Life expectancy by continent, 2007",
       x = NULL, y = "Life expectancy (years)")
ggsave("figures/02_lifeexp_box_continent.png", p2, width = 8, height = 5, dpi = 150)

# GDP is heavily right-skewed, so compare raw vs log scale
cat("\nSkewness check (mean vs median of GDP per capita, 2007):\n")
print(gap %>% filter(year == 2007) %>%
        summarise(mean = mean(gdpPercap), median = median(gdpPercap)))

# ---- 4. Relationships ----------------------------------------
p3 <- ggplot(filter(gap, year == 2007),
             aes(gdpPercap, lifeExp, size = pop, colour = continent)) +
  geom_point(alpha = 0.7) +
  scale_x_log10(labels = label_dollar()) +
  scale_size(range = c(1, 12), guide = "none") +
  labs(title = "Wealth and health, 2007",
       subtitle = "GDP per capita on a log scale; bubble size shows population",
       x = "GDP per capita (log scale, inflation-adjusted US$)",
       y = "Life expectancy (years)", colour = NULL)
ggsave("figures/03_wealth_health_2007.png", p3, width = 9, height = 6, dpi = 150)

cor_raw <- with(filter(gap, year == 2007), cor(gdpPercap, lifeExp))
cor_log <- with(filter(gap, year == 2007), cor(log10(gdpPercap), lifeExp))
cat(sprintf("\nCorrelation (2007): raw GDP r = %.3f | log10 GDP r = %.3f\n",
            cor_raw, cor_log))

# ---- 5. Trends over time -------------------------------------
trend <- gap %>%
  group_by(continent, year) %>%
  summarise(median_lifeExp = median(lifeExp), .groups = "drop")

p4 <- ggplot(trend, aes(year, median_lifeExp, colour = continent)) +
  geom_line(linewidth = 1.1) + geom_point() +
  labs(title = "Median life expectancy by continent, 1952 to 2007",
       x = NULL, y = "Median life expectancy (years)", colour = NULL)
ggsave("figures/04_trend_continent.png", p4, width = 9, height = 5.5, dpi = 150)

gains <- gap %>%
  filter(year %in% c(1952, 2007)) %>%
  select(country, continent, year, lifeExp) %>%
  pivot_wider(names_from = year, values_from = lifeExp, names_prefix = "y") %>%
  mutate(gain = y2007 - y1952) %>%
  arrange(desc(gain))
cat("\nLargest gains in life expectancy, 1952 to 2007:\n"); print(head(gains, 5))
cat("\nSmallest gains (or losses):\n");                   print(tail(gains, 5))
write.csv(gains, "output/lifeexp_gains_1952_2007.csv", row.names = FALSE)

# ---- 6. Focus: Nigeria and West African peers ----------------
peers <- c("Nigeria", "Ghana", "Senegal", "Cote d'Ivoire", "Benin", "Niger")
wa <- gap %>% filter(country %in% peers)

p5 <- ggplot(wa, aes(year, lifeExp, colour = country)) +
  geom_line(linewidth = 1) +
  geom_line(data = filter(trend, continent == "Africa"),
            aes(year, median_lifeExp), inherit.aes = FALSE,
            linetype = "dashed", colour = "grey30") +
  labs(title = "Nigeria and West African peers: life expectancy",
       subtitle = "Dashed line shows the African median",
       x = NULL, y = "Life expectancy (years)", colour = NULL)
ggsave("figures/05_nigeria_peers.png", p5, width = 9, height = 5.5, dpi = 150)

nigeria <- gap %>% filter(country == "Nigeria") %>%
  select(year, lifeExp, gdpPercap, pop)
print(nigeria)
write.csv(nigeria, "output/nigeria_profile.csv", row.names = FALSE)

# Nigeria's rank within Africa in 2007
rank_2007 <- gap %>% filter(year == 2007, continent == "Africa") %>%
  mutate(rank_lifeExp = rank(-lifeExp), rank_gdp = rank(-gdpPercap)) %>%
  filter(country == "Nigeria") %>% select(country, lifeExp, rank_lifeExp, gdpPercap, rank_gdp)
cat("\nNigeria's rank among", sum(gap$year == 2007 & gap$continent == "Africa"),
    "African countries in 2007:\n"); print(rank_2007)

# ---- 7. Outliers ----------------------------------------------
# Countries whose life expectancy fell between any two consecutive surveys
drops <- gap %>% arrange(country, year) %>% group_by(country) %>%
  mutate(change = lifeExp - lag(lifeExp)) %>%
  filter(change < -3) %>% select(country, continent, year, lifeExp, change) %>%
  arrange(change)
cat("\nSharp drops in life expectancy (more than 3 years between surveys):\n")
print(drops, n = 20)
write.csv(drops, "output/sharp_drops.csv", row.names = FALSE)

sessionInfo()
