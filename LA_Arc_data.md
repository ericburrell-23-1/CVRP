# How Many Arcs Are Being Generated

The following shows the count of arcs and terms in P+ generated with the current logic. The table shows what happens when the number of customers |N| = 31 and the number of LA Neighbors per customer K = 8. The column labeled `|N| x K x C(n,r)` represents the expected number of combinations of `(u, v, N_hat)` that can exist for a set `N_hat` containing `r` intermediate customers.

| r   | P+ (v cannot be in w's LA neighbor set) | P      | P+ - P | N x K x C(n,r) |
| --- | --------------------------------------- | ------ | ------ | -------------- |
| 0   | 713                                     | 713    | 0      | 713            |
| 1   | 10768                                   | 5704   | 5064   | 5704           |
| 2   | 52234                                   | 19964  | 32270  | 19964          |
| 3   | 122744                                  | 39928  | 82816  | 39928          |
| 4   | 160096                                  | 110186 | 110186 | 49910          |
| 5   | 120175                                  | 39928  | 80247  | 39928          |
| 6   | 50249                                   | 19964  | 30285  | 19964          |
| 7   | 10364                                   | 5704   | 4660   | 5704           |
| 8   | 713                                     | 713    | 0      | 713            |
