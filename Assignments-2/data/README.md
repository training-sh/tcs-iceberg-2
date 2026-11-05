# Olist assignment data

[olist-four-datasets.zip](olist-four-datasets.zip) contains four unchanged CSVs selected from the supplied Olist archive: customers, orders, order items and order payments. [manifest.csv](manifest.csv) records each file's SHA-256, byte size and data-row count excluding its header. No rows were sampled, added or transformed. The selection omits the other original source files.

Source: **Olist**, [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Thanks to Olist and its collaborators for making the dataset available. The publisher describes anonymized Brazilian ecommerce orders from 2016–2018.

Dataset license: [Creative Commons Attribution–NonCommercial–ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/), as listed on the source dataset page. Preserve this attribution and the dataset's license when sharing the bundled data; the dataset license applies to these CSVs independently of any repository code license.

Extract this ZIP beside the notebook, verify its files against the manifest, and copy the original bytes into the assignment's Bronze prefixes as described in the [assignment](../README.md). CSVs retain their original filenames. Upload the ZIP itself only to notebook-local storage, not to a Bronze dataset prefix.

Archive size: **21,061,474 bytes (20.09 MiB)**. Uncompressed CSV total: **47,904,680 bytes (45.69 MiB)**. ZIP SHA-256:

```text
44863a941eee78710538d1aaeacaf82064ca55288fa460c3d318c167b4effd9d
```

The ZIP is below GitHub's [25 MiB browser-upload limit](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository). Keep it compressed in the repository; no Git LFS is needed for this file. Upload `manifest.csv` and this attribution file alongside it.
