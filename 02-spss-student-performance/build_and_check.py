"""Builds the labelled SPSS file and independently checks the results the SPSS syntax produces."""
import pandas as pd, numpy as np, pyreadstat
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

df = pd.read_csv("data/student-mat.csv", sep=";")
yn = {"yes": 1, "no": 0}
out = pd.DataFrame({
    "id": range(1, len(df) + 1),
    "school": df.school.map({"GP": 1, "MS": 2}),
    "sex": df.sex.map({"F": 1, "M": 2}),
    "age": df.age,
    "address": df.address.map({"U": 1, "R": 2}),
    "medu": df.Medu, "fedu": df.Fedu,
    "traveltime": df.traveltime, "studytime": df.studytime,
    "failures": df.failures,
    "schoolsup": df.schoolsup.map(yn), "famsup": df.famsup.map(yn),
    "paid": df.paid.map(yn), "higher": df.higher.map(yn),
    "internet": df.internet.map(yn),
    "famrel": df.famrel, "goout": df.goout, "health": df.health,
    "absences": df.absences, "G1": df.G1, "G2": df.G2, "G3": df.G3,
})
var_labels = {
    "id": "Student ID", "school": "School", "sex": "Sex", "age": "Age (years)",
    "address": "Home address type", "medu": "Mother's education", "fedu": "Father's education",
    "traveltime": "Home to school travel time", "studytime": "Weekly study time",
    "failures": "Number of past class failures", "schoolsup": "Extra educational support from school",
    "famsup": "Family educational support", "paid": "Extra paid maths classes",
    "higher": "Wants to take higher education", "internet": "Internet access at home",
    "famrel": "Quality of family relationships (1-5)", "goout": "Going out with friends (1-5)",
    "health": "Current health status (1-5)", "absences": "Number of school absences",
    "G1": "First period grade (0-20)", "G2": "Second period grade (0-20)", "G3": "Final grade (0-20)",
}
ynl = {0: "No", 1: "Yes"}
edu = {0: "None", 1: "Primary (4th grade)", 2: "5th to 9th grade", 3: "Secondary", 4: "Higher education"}
value_labels = {
    "school": {1: "Gabriel Pereira", 2: "Mousinho da Silveira"}, "sex": {1: "Female", 2: "Male"},
    "address": {1: "Urban", 2: "Rural"}, "medu": edu, "fedu": edu,
    "traveltime": {1: "<15 min", 2: "15-30 min", 3: "30-60 min", 4: ">1 hour"},
    "studytime": {1: "<2 hours", 2: "2-5 hours", 3: "5-10 hours", 4: ">10 hours"},
    **{v: ynl for v in ["schoolsup", "famsup", "paid", "higher", "internet"]},
}
measure = {v: "nominal" for v in ["id","school","sex","address","schoolsup","famsup","paid","higher","internet"]}
measure.update({v: "ordinal" for v in ["medu","fedu","traveltime","studytime","famrel","goout","health"]})
measure.update({v: "scale" for v in ["age","failures","absences","G1","G2","G3"]})
pyreadstat.write_sav(out, "data/student_performance.sav", column_labels=var_labels,
                     variable_value_labels=value_labels, variable_measure=measure)

# ---------- independent check of results ----------
print("All students:", len(out), "| G3 = 0:", (out.G3 == 0).sum())
d = out[out.G3 > 0].copy()
print("Analysed (sat final exam):", len(d))
print(d[["G3","absences","failures","age"]].describe().round(2).T)

def ttest(var, labels):
    a, b = [d.loc[d[var] == k, "G3"] for k in labels]
    lev = stats.levene(a, b, center="mean")
    t_eq = stats.ttest_ind(a, b, equal_var=True); t_w = stats.ttest_ind(a, b, equal_var=False)
    sp = np.sqrt(((len(a)-1)*a.var() + (len(b)-1)*b.var()) / (len(a)+len(b)-2))
    print(f"\n{var}: n={len(a)},{len(b)} means={a.mean():.2f},{b.mean():.2f} sd={a.std():.2f},{b.std():.2f}"
          f" Levene F={lev.statistic:.3f} p={lev.pvalue:.3f} | t(eq)={t_eq.statistic:.3f} p={t_eq.pvalue:.4f}"
          f" | Welch t={t_w.statistic:.3f} p={t_w.pvalue:.4f} | d={(a.mean()-b.mean())/sp:.2f}")
ttest("sex", [1, 2]); ttest("higher", [1, 0]); ttest("internet", [1, 0]); ttest("schoolsup", [1, 0])

g = [d.loc[d.studytime == k, "G3"] for k in [1,2,3,4]]
print("\nStudytime means:", [round(x.mean(),2) for x in g], "n:", [len(x) for x in g])
F = stats.f_oneway(*g); print("ANOVA F=%.3f p=%.4f" % (F.statistic, F.pvalue))
print("Levene:", stats.levene(*g, center="mean"))
ss_b = sum(len(x)*(x.mean()-d.G3.mean())**2 for x in g); ss_t = ((d.G3-d.G3.mean())**2).sum()
print("eta^2 = %.3f" % (ss_b/ss_t))
print(pairwise_tukeyhsd(d.G3, d.studytime))

f = [d.loc[d.failures.clip(upper=1) == k, "G3"] for k in [0, 1]]

print("\nPearson correlations with G3:")
for v in ["G1","G2","failures","absences","medu","fedu","age","goout","studytime"]:
    r, p = stats.pearsonr(d[v], d.G3); print(f"  {v:10s} r={r:.3f} p={p:.4f}")
print("Spearman G3~absences:", stats.spearmanr(d.absences, d.G3))

out["pass"] = (out.G3 >= 10).astype(int)
for v in ["higher", "schoolsup", "address"]:
    ct = pd.crosstab(out[v], out["pass"]); chi = stats.chi2_contingency(ct, correction=False)
    print(f"\nChi-square pass by {v} (all {len(out)} students):\n{ct}\n row % pass: {(ct[1]/ct.sum(1)*100).round(1).tolist()}"
          f"\n chi2={chi[0]:.3f} df={chi[2]} p={chi[1]:.4f} min expected={chi[3].min():.2f}"
          f" phi={np.sqrt(chi[0]/ct.values.sum()):.3f}")
    if (chi[3] < 5).any(): print(" Fisher exact p=%.4f" % stats.fisher_exact(ct)[1])
