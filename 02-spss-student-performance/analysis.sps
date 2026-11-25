* Encoding: UTF-8.
* =============================================================.
* Project 2: Factors Associated with Secondary School Maths Performance.
* Dataset : UCI Student Performance (Cortez and Silva, 2008), maths course, n = 395.
* Author  : Princess Ijeoma Agudosi.
* Tool    : IBM SPSS Statistics.
* Run     : open this file in SPSS, set the path below, then Run > All.
* =============================================================.

* Change this path to where you saved the data file.
GET FILE='data/student_performance.sav'.
DATASET NAME students WINDOW=FRONT.

* ---- 1. Data screening --------------------------------------.
FREQUENCIES VARIABLES=sex school address studytime higher internet schoolsup failures
  /ORDER=ANALYSIS.

DESCRIPTIVES VARIABLES=age absences G1 G2 G3
  /STATISTICS=MEAN STDDEV MIN MAX SKEWNESS KURTOSIS.

* 38 students scored 0 on the final grade although most had non-zero earlier grades.
* This pattern suggests they did not sit the final exam, so they are treated separately.
COMPUTE sat_exam = (G3 > 0).
VARIABLE LABELS sat_exam 'Sat the final exam'.
VALUE LABELS sat_exam 0 'No (G3 = 0)' 1 'Yes'.
FREQUENCIES VARIABLES=sat_exam.

* ---- 2. Pass rate (all 395 students) -------------------------.
* Pass = final grade of 10 or more out of 20. Not sitting the exam counts as not passing.
COMPUTE pass = (G3 >= 10).
VARIABLE LABELS pass 'Passed final maths (G3 >= 10)'.
VALUE LABELS pass 0 'Did not pass' 1 'Passed'.
EXECUTE.

CROSSTABS
  /TABLES=higher schoolsup address BY pass
  /STATISTICS=CHISQ PHI
  /CELLS=COUNT ROW EXPECTED
  /COUNT ROUND CELL.

* ---- 3. Restrict to students who sat the final exam (n = 357) -.
USE ALL.
FILTER BY sat_exam.
EXECUTE.

* Normality and outlier checks for the outcome.
EXAMINE VARIABLES=G3
  /PLOT BOXPLOT HISTOGRAM NPPLOT
  /STATISTICS DESCRIPTIVES
  /MISSING LISTWISE.

* ---- 4. Independent-samples t-tests --------------------------.
T-TEST GROUPS=sex(1 2)
  /VARIABLES=G3
  /ES DISPLAY(TRUE)
  /CRITERIA=CI(.95).

T-TEST GROUPS=higher(1 0)
  /VARIABLES=G3
  /ES DISPLAY(TRUE)
  /CRITERIA=CI(.95).

T-TEST GROUPS=internet(1 0)
  /VARIABLES=G3
  /ES DISPLAY(TRUE)
  /CRITERIA=CI(.95).

T-TEST GROUPS=schoolsup(1 0)
  /VARIABLES=G3
  /ES DISPLAY(TRUE)
  /CRITERIA=CI(.95).

* ---- 5. One-way ANOVA: final grade by weekly study time -------.
ONEWAY G3 BY studytime
  /ES=OVERALL
  /STATISTICS DESCRIPTIVES HOMOGENEITY WELCH
  /PLOT MEANS
  /MISSING ANALYSIS
  /POSTHOC=TUKEY GH ALPHA(0.05).

* ---- 6. Correlations ----------------------------------------.
CORRELATIONS
  /VARIABLES=G3 G1 G2 failures absences medu fedu age goout studytime
  /PRINT=TWOTAIL NOSIG
  /MISSING=PAIRWISE.

* Absences are heavily skewed, so check with Spearman's rho as well.
NONPAR CORR
  /VARIABLES=G3 absences failures
  /PRINT=SPEARMAN TWOTAIL NOSIG
  /MISSING=PAIRWISE.

* ---- 7. Charts ----------------------------------------------.
GRAPH /BAR(SIMPLE)=MEAN(G3) BY studytime /INTERVAL CI(95.0).
GRAPH /SCATTERPLOT(BIVAR)=absences WITH G3.

FILTER OFF.
USE ALL.
