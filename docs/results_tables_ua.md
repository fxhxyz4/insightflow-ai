# Таблиці для Розділу 3 (згенеровано eval/make_tables.py)


### Таблиця 1. Класифікація за категоріями (ручна вибірка)

| Метод | n | accuracy | macro-F1 | F1 mixed | F1 thematic | с/новину |
|---|---|---|---|---|---|---|
| baseline_tfidf_logreg | 137 | 0.6934 | 0.7117 | 0.3579 | 0.8521 | 0.008 |
| llm_phi | 137 | 0.7518 | 0.7383 | 0.7136 | 0.7335 | 2.236 |
| llm_qwen3 | 137 | 0.7007 | 0.6688 | 0.2781 | 0.7631 | 3.512 |

### Таблиця 2 (уся вибірка, n = 137). 95% довірчі інтервали (bootstrap)

| method | accuracy | macro_f1 | d_accuracy | d_macro_f1 |
|---|---|---|---|---|
| baseline_tfidf_logreg | 0.693 [0.620, 0.766] | 0.712 [0.633, 0.776] |  |  |
| llm_phi | 0.752 [0.679, 0.825] | 0.738 [0.651, 0.809] | +0.058 [-0.051, +0.161] | +0.027 [-0.084, +0.132] |
| llm_qwen3 | 0.701 [0.628, 0.774] | 0.669 [0.567, 0.747] | +0.007 [-0.102, +0.102] | -0.043 [-0.151, +0.055] |

### Таблиця 2 (змішані фіди, n = 54). 95% довірчі інтервали (bootstrap)

| method | accuracy | macro_f1 | d_accuracy | d_macro_f1 |
|---|---|---|---|---|
| baseline_tfidf_logreg | 0.444 [0.315, 0.593] | 0.358 [0.241, 0.488] |  |  |
| llm_phi | 0.778 [0.667, 0.889] | 0.714 [0.468, 0.851] | +0.333 [+0.167, +0.500]* | +0.356 [+0.088, +0.534]* |
| llm_qwen3 | 0.611 [0.481, 0.741] | 0.278 [0.204, 0.389] | +0.167 [+0.000, +0.333] | -0.080 [-0.210, +0.050] |

### Таблиця 2 (тематичні фіди, n = 83). 95% довірчі інтервали (bootstrap)

| method | accuracy | macro_f1 | d_accuracy | d_macro_f1 |
|---|---|---|---|---|
| baseline_tfidf_logreg | 0.855 [0.783, 0.928] | 0.852 [0.772, 0.918] |  |  |
| llm_phi | 0.735 [0.639, 0.831] | 0.734 [0.627, 0.821] | -0.120 [-0.241, +0.000] | -0.119 [-0.249, +0.001] |
| llm_qwen3 | 0.759 [0.663, 0.843] | 0.763 [0.654, 0.848] | -0.096 [-0.229, +0.036] | -0.089 [-0.219, +0.035] |

`*` у стовпцях d_* означає, що інтервал різниці з baseline не містить 0.

### Таблиця 3. Агент з інструментами проти тієї ж моделі без інструментів

| model | n | agent_tool_ok | agent_success | plain_success | agent_sec_per_query |
|---|---|---|---|---|---|
| phi | 15 | 1.0 | 0.2 | 0.0 | 398.7 |
| qwen3 | 15 | 1.0 | 0.13333333333333333 | 0.0 | 118.9 |

### Таблиця 4. Запити, які агент не пройшов автоматично (розбір вручну)

| Модель | # | Запит | tool_ok | grounded | finished | Відповідь (початок) | Причина (заповнити вручну) |
|---|---|---|---|---|---|---|---|
| phi | 1 | Give me a summary of today's economics news. | True | False | True | There are no new economics news available for today. |  |
| phi | 2 | Дай зведення новин з програмування за сьогодні. | True | False | True | There are no new programming news for today. |  |
| phi | 3 | Summarize the latest design news for me. | True | False | True | There are currently no new design news to summarize. |  |
| phi | 4 | Зроби дайджест по маркетингу. | True | False | False |  |  |
| phi | 5 | What happened in science today? Give me a digest. | True | False | True | There are no new science news articles for today. |  |
| phi | 6 | Дай зведення світових новин за сьогодні. | True | False | True | There are currently no global news articles available for today. |  |
| phi | 7 | What are the latest headlines in economics? | True | False | True | There are currently no latest headlines in the economics category. |  |
| phi | 8 | Що нового в програмуванні? Покажи заголовки. | True | False | True | No new articles have been found in the programming category at the moment. You might want to check back later or explore |  |
| phi | 9 | List the newest design headlines. | True | False | True | No new headlines were found in the 'design' category. |  |
| phi | 10 | Які свіжі новини з маркетингу? | True | False | True | Here are some of the latest marketing news articles:  1. "TikTok accused of helping to promote sex industry to girls" -  |  |
| phi | 11 | Show me today's science headlines. | True | False | True | I'm sorry, but there are no science news headlines available for today. |  |
| phi | 12 | What are the main world news right now? | True | False | True | The main world news currently includes the following topics:  1. Israel’s president has chosen Yashar leader Gadi Eisenk |  |
| qwen3 | 1 | Give me a summary of today's economics news. | True | False | True | There are no recent economics news articles available today. |  |
| qwen3 | 2 | Дай зведення новин з програмування за сьогодні. | True | False | True | З категорії "programing" за сьогодні (2026-11-09) новин немає. |  |
| qwen3 | 3 | Summarize the latest design news for me. | True | False | True | There are no recent design news articles available in the database. |  |
| qwen3 | 4 | Зроби дайджест по маркетингу. | True | False | True | У категорії "маркетинг" немає останніх новин. |  |
| qwen3 | 5 | What happened in science today? Give me a digest. | True | False | False | <think> Okay, let me try to figure this out. The user asked for science news today and initially tried to build a digest |  |
| qwen3 | 6 | Дай зведення світових новин за сьогодні. | True | False | True | Для сьогодні, 2026-11-09, в категорії "світ" немає новин. |  |
| qwen3 | 7 | What are the latest headlines in economics? | True | False | True | There are no recent headlines in the economics category. |  |
| qwen3 | 8 | Що нового в програмуванні? Покажи заголовки. | True | False | True | Новини з програмування:   1. **Five memorable books about programming** (Hacker News, 2026-11-07)   2. **A Treatise on M |  |
| qwen3 | 9 | List the newest design headlines. | True | False | True | No recent design headlines were found in the database for the specified date. |  |
| qwen3 | 10 | Які свіжі новини з маркетингу? | True | False | True | Згідно з оновленими даними, ось свіжі новини, пов’язані з маркетингом:   1. **TikTok accused of helping to promote sex i |  |
| qwen3 | 11 | Show me today's science headlines. | True | False | True | There are no recent science news articles available for today, 2026-11-09. |  |
| qwen3 | 12 | What are the main world news right now? | True | False | True | There are no recent world news articles available in the database. |  |
| qwen3 | 15 | Find news about Amazon. | True | False | True | Here are the news articles related to Amazon:   1. **Amazon’s new basic Kindle proves you don’t need all the bells and w |  |
