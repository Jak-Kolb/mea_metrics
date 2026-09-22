# Screening report — all Adam recordings (B2)

Same frozen thresholds as B1 (`LIBRARY_NOTES.md`). Treatment bar: *no culture holdout*; n=1 culture per recording.

## Per-recording summary

| recording | PASS | FAIL | SKIP | report |
|---|---:|---:|---:|---|
| `SMJM_Bicuculline` | 37 | 6 | 1 | `reports/screen/SCREEN_REPORT_SMJM_Bicuculline.md` |
| `ER52_ImpactWithBicuculline` | 28 | 15 | 1 | `reports/screen/SCREEN_REPORT_ER52_ImpactWithBicuculline.md` |
| `JMSM_ImpactWithoutBicuculline` | 39 | 4 | 1 | `reports/screen/SCREEN_REPORT_JMSM_ImpactWithoutBicuculline.md` |
| `SM_pHshock` | 37 | 6 | 1 | `reports/screen/SCREEN_REPORT_SM_pHshock.md` |

## Failure roll-up

### `SMJM_Bicuculline`

- **isi_mean_s / beyond_rate**: Spearman(metric, rate_hz)=-0.997
- **isi_mean_s / treatment_response**: Cohen_d(post−baseline)=-0.254  *n=1 culture (SMJM), no holdout yet*
- **isi_median_s / treatment_response**: Cohen_d(post−baseline)=-0.104  *n=1 culture (SMJM), no holdout yet*
- **burst_count / beyond_rate**: Spearman(metric, rate_hz)=0.929
- **mean_ibi_s / beyond_rate**: Spearman(metric, rate_hz)=-0.909
- **n_spikes / beyond_rate**: Spearman(metric, rate_hz)=1.000

### `ER52_ImpactWithBicuculline`

- **rate_hz / treatment_response**: Cohen_d(post−baseline)=-0.002  *n=1 culture (SMJM), no holdout yet*
- **isi_mean_s / beyond_rate**: Spearman(metric, rate_hz)=-0.998
- **isi_mean_s / treatment_response**: Cohen_d(post−baseline)=-0.151  *n=1 culture (SMJM), no holdout yet*
- **isi_median_s / beyond_rate**: Spearman(metric, rate_hz)=-0.923
- **isi_median_s / treatment_response**: Cohen_d(post−baseline)=-0.138  *n=1 culture (SMJM), no holdout yet*
- **cv_isi / beyond_rate**: Spearman(metric, rate_hz)=0.973
- **cv_isi / treatment_response**: Cohen_d(post−baseline)=-0.079  *n=1 culture (SMJM), no holdout yet*
- **burst_count / treatment_response**: Cohen_d(post−baseline)=0.130  *n=1 culture (SMJM), no holdout yet*
- **burst_spike_frac / beyond_rate**: Spearman(metric, rate_hz)=0.950
- **burst_spike_frac / treatment_response**: Cohen_d(post−baseline)=0.009  *n=1 culture (SMJM), no holdout yet*
- **mean_ibi_s / treatment_response**: Cohen_d(post−baseline)=-0.106  *n=1 culture (SMJM), no holdout yet*
- **sttc_mean_unit / treatment_response**: Cohen_d(post−baseline)=0.187  *n=1 culture (SMJM), no holdout yet*
- **n_spikes / beyond_rate**: Spearman(metric, rate_hz)=1.000
- **n_spikes / treatment_response**: Cohen_d(post−baseline)=-0.002  *n=1 culture (SMJM), no holdout yet*
- **sttc_mean_window / baseline_stability**: window split-half Spearman=0.033; CV across baseline=0.036

### `JMSM_ImpactWithoutBicuculline`

- **isi_mean_s / beyond_rate**: Spearman(metric, rate_hz)=-0.997
- **burst_count / beyond_rate**: Spearman(metric, rate_hz)=0.941
- **n_spikes / beyond_rate**: Spearman(metric, rate_hz)=1.000
- **sttc_mean_window / baseline_stability**: window split-half Spearman=0.168; CV across baseline=0.037

### `SM_pHshock`

- **isi_mean_s / beyond_rate**: Spearman(metric, rate_hz)=-1.000
- **isi_median_s / beyond_rate**: Spearman(metric, rate_hz)=-0.954
- **burst_count / beyond_rate**: Spearman(metric, rate_hz)=0.933
- **mean_ibi_s / treatment_response**: Cohen_d(post−baseline)=0.077  *n=1 culture (SMJM), no holdout yet*
- **sttc_degree / treatment_response**: Cohen_d(post−baseline)=-0.200  *n=1 culture (SMJM), no holdout yet*
- **n_spikes / beyond_rate**: Spearman(metric, rate_hz)=1.000
