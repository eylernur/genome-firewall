# Genome Firewall — held-out evaluation

Species: **Klebsiella pneumoniae**  |  test genomes: 179


## Summary
| drug          |   n_test |   prevalence_R |   balanced_acc |   recall_R |   recall_S |    f1 |   AUROC |   PR_AUC |   Brier |   nocall_rate |   acc_on_calls |
|:--------------|---------:|---------------:|---------------:|-----------:|-----------:|------:|--------:|---------:|--------:|--------------:|---------------:|
| ciprofloxacin |      162 |          0.321 |          0.929 |      0.885 |      0.973 | 0.911 |   0.955 |    0.95  |   0.045 |         0     |          0.944 |
| gentamicin    |      170 |          0.2   |          0.93  |      0.882 |      0.978 | 0.896 |   0.941 |    0.885 |   0.042 |         0     |          0.959 |
| meropenem     |      164 |          0.177 |          0.903 |      0.828 |      0.978 | 0.857 |   0.976 |    0.815 |   0.048 |         0     |          0.951 |
| ceftazidime   |      152 |          0.388 |          0.935 |      0.881 |      0.989 | 0.929 |   0.964 |    0.957 |   0.046 |         0.046 |          0.966 |


## ciprofloxacin

| drug          |   n_test |   prevalence_R |   balanced_acc |   recall_R |   recall_S |    f1 |   AUROC |   PR_AUC |   Brier |   nocall_rate |   acc_on_calls |
|:--------------|---------:|---------------:|---------------:|-----------:|-----------:|------:|--------:|---------:|--------:|--------------:|---------------:|
| ciprofloxacin |      162 |          0.321 |          0.929 |      0.885 |      0.973 | 0.911 |   0.955 |     0.95 |   0.045 |             0 |          0.944 |

_Groups in test: 52 (balanced acc reported per group where both classes present)_


## gentamicin

| drug       |   n_test |   prevalence_R |   balanced_acc |   recall_R |   recall_S |    f1 |   AUROC |   PR_AUC |   Brier |   nocall_rate |   acc_on_calls |
|:-----------|---------:|---------------:|---------------:|-----------:|-----------:|------:|--------:|---------:|--------:|--------------:|---------------:|
| gentamicin |      170 |            0.2 |           0.93 |      0.882 |      0.978 | 0.896 |   0.941 |    0.885 |   0.042 |             0 |          0.959 |

_Groups in test: 56 (balanced acc reported per group where both classes present)_


## meropenem

| drug      |   n_test |   prevalence_R |   balanced_acc |   recall_R |   recall_S |    f1 |   AUROC |   PR_AUC |   Brier |   nocall_rate |   acc_on_calls |
|:----------|---------:|---------------:|---------------:|-----------:|-----------:|------:|--------:|---------:|--------:|--------------:|---------------:|
| meropenem |      164 |          0.177 |          0.903 |      0.828 |      0.978 | 0.857 |   0.976 |    0.815 |   0.048 |             0 |          0.951 |

_Groups in test: 54 (balanced acc reported per group where both classes present)_


## ceftazidime

| drug        |   n_test |   prevalence_R |   balanced_acc |   recall_R |   recall_S |    f1 |   AUROC |   PR_AUC |   Brier |   nocall_rate |   acc_on_calls |
|:------------|---------:|---------------:|---------------:|-----------:|-----------:|------:|--------:|---------:|--------:|--------------:|---------------:|
| ceftazidime |      152 |          0.388 |          0.935 |      0.881 |      0.989 | 0.929 |   0.964 |    0.957 |   0.046 |         0.046 |          0.966 |

_Groups in test: 47 (balanced acc reported per group where both classes present)_
