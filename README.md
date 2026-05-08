# Sci-ModHub

Sci-ModoM UCSC track hub generator. **scimodhub** fetches metadata and data from [Sci-ModoM](https://scimodom.dieterichlab.org) and builds a track hub using a *faceted composite*, by modification, cell type, tissue or organism, and technology.

<p align="center">
  <a href="https://trackhub.dieterichlab.org/eboileau/SciModHub/"><img alt="Sci-ModHub" src="https://github.com/eboileau/scimodhub/blob/main/docs/source/_static/logo_hub.png"></a>
</p>

---

## Documentation

### Install

```bash
pip install -e .
```

### Kent binaries

Copy the application binaries

```bash
cd scripts
./copy_ucsc_exe
```

and make them visible. `bedToBigBed` is required; the others are optional. Chromosome information is downloaded from Sci-ModoM or, optionally, using `fetchChromSizes`.

### Usage and configuration

To build a track hub, **scimodhub** needs a list of bedRmod files and associated metadata. To prepare this list and download the required data, use the `fetch` command with `metadata_table: null`. A `metadata_table` can also be given as input to the `build` command. This table contains one row per dataset file. Required columns are:

| header | value |
| :---   | :---  |
| dataset_id | EUFID or dataset ID |
|project_id| SMID or project ID |
|taxa_id| NCBI Taxonomic ID |
|rna| A valid RNA type |
|tech| Technology |
|modomics_sname| MODOMICS short name |
|cto| cell, tissue, or organism |
|bedrmod_path | Path to bedRmod file |

For more details on the meaning of these columns, consult the [Sci-ModoM documentation](https://scimodom.dieterichlab.org/documentation/about) or the latest [EUF specs](https://dieterich-lab.github.io/euf-specs/).

To download *chrom.sizes* from Sci-ModoM, use

```yaml
genomes:
  h_sapiens:
    taxa_id: 9606
    assembly:
      GRCh38: "hg38"
    chrom:
      mapping: data/GRCh38_ensembl2UCSC.tsv
      sizes: null
```

If calling `fetch` first, `metadata_table` and `chrom.sizes` do not need to be updated, the `build` call will recognize the downloaded files automatically. If values are given for any one or both of these, the `fetch` call will skip download, and `build` will use these values to read in the corresponding files. The chromosome information must follow the UCSC nomenclature. The `chrom.mapping` is **always** required. This table contains one row per chromosome, without a header. Required columns are:

| columns 1 | columns 2 |
| :--- | :--- |
| Ensembl | UCSC |

The content of these files (chromosome and mapping) is not validated.

The directories given by `working_dir` and `staging_dir` are created on demand and their content is always overwritten. To remove these directories use `clean`.

For further configuration parameters, see the [example configuration file](data/examples/config.yaml).

#### Score

The `score_policy` defines how to handle the bedRmod score. According to EUF [version 1.8](https://dieterich-lab.github.io/euf-specs/bedRModv1.8.pdf), score is `Int [0, 1000]`. The latest specifications ([version 2](https://dieterich-lab.github.io/euf-specs/bedRModv2.pdf)) allow any representation or measure of confidence by defining score as `String [\x20-\x7e]{1,255}`. This provides in the short-to-medium-term a lightweight, flexible, and backward compatible framework that allows for immediate and broad usability, while leaving room for versioned improvements.

The EUF specifications aim to provide guidelines for data representation and data sharing, not for estimating modification truth in general (this is a different question!). As data specs in general, they want to remain as close as possible to the raw evidence, to facilitate interoperability and reusability across disciplines. For practical purposes, and with this aim in mind, the official recommendation is to use for score the *valid coverage* which, in combination with total coverage and frequency, provides a reasonable, robust means of accumulating or comparing site evidence across datasets. This definition is 'natural' and straightforward for Nanopore, *cf.* [modkit](https://nanoporetech.github.io/modkit), but has lead to discussion regarding it's suitability for short-read-based detection technologies. Meanwhile, we need a practical solution.

A lot of existing short-read data are just not *quantitative* enough to be included in Sci-ModoM. These data not only fall short of providing any measure of confidence whatsoever, but in most cases, the authors did not even release enough information to 'fill in' the missing pieces (that's precisely why EUF specifications are important!).

As Sci-ModoM is preparing to move from EUF version 1.8 to 2, *ad hoc* or missing scores will be replaced by their corresponding site coverage. While this duplicates data, this does not generally lead to loss of information. To build a track hub using the data from the current version of Sci-ModoM (v4.0.2, EUF specs v1.8), but consistently with the latest EUF specs v2 (with the limitation that valid coverage is replaced by coverage, as explained above), use `score_policy: coverage`.

Note that a bedRMod file with score values outside the range [0, 1000] may not only fail from being correctly displayed (*cf.* [bedtools definition of score](https://bedtools.readthedocs.io/en/latest/content/general-usage.html?highlight=bed%20format)), it will also fail to convert to bigBed! For this reason, score-based shading and filtering is disabled, and score is set to zero. The 'original' score value is stored in a additional 12th field, which is used *e.g.* for display.

### Commands


#### Fetch

Download metadata and data (bedRmod files) from [Sci-ModoM](https://scimodom.dieterichlab.org) for organisms specified in the configuration file.

```bash
scimodhub --config data/examples/config.yaml fetch --eufid [EUFID ...]
```

Use `--eufid` to download selected datasets only.

#### Build

```bash
scimodhub --config data/examples/config.yaml build
```

Use `--skip-call` to create hub but skip calls to `bedToBigBed`.

#### Clean

```bash
scimodhub --config data/examples/config.yaml clean
```

### Troubleshooting

The TrackDb shortLabel is limited to 17 printable characters. This label is a composite of two values given in the configuration file. If this fail with `pydantic_core._pydantic_core.ValidationError ... short_label ... String should have at most 17 characters`, change values in the configuration file.

## Development notes

### Testing

Install test dependencies

```bash
pip install -e .[tests]
# or
pip install -r requirements-dev.txt
```

and

```bash
pytest tests
```

### Limitations

* The bedRmod header is only validated for EUF version and assembly; the assembly is specified in the metadata table or via the configuration file. If both are given, their version must match. If the assembly is missing from the metadata table, it is automatically 'filled' with that from the configuration file. There is currently no API endpoint to query the Sci-ModoM assembly version. During `fetch`, the assembly is added to the metadata table using the value from the configuration file.

* Record validation is similar to that performed during [data upload via Sci-ModoM](https://scimodom.dieterichlab.org/documentation/management), except for chromosomes and modification names, but since data files are assumed to come directly from Sci-ModoM, records should already satisfy strict requirements.

* The list of datasets is filtered *on the fly* for each organism; the API endpoint does not currently allow query parameters.

### Issues

* `hubCheck` returns

```
warning: missing description page for track. Add 'html SciModoM.html' line to the 'SciModoM' track stanza.
warning: missing description page for track. Add 'html SciModoM_dataset00001Y.html' line to the 'SciModoM_dataset00001Y' track stanza.
warning: missing description page for track. Add 'html SciModoM_dataset00001m6A.html' line to the 'SciModoM_dataset00001m6A' track stanza.
warning: missing description page for track. Add 'html SciModoM_dataset00002Y.html' line to the 'SciModoM_dataset00002Y' track stanza.
warning: missing description page for track. Add 'html SciModoM_dataset00003m6A.html' line to the 'SciModoM_dataset00003m6A' track stanza.
```


### Todos

* Organisms given in the configuration file are not 'validated' against those available in Sci-ModoM.

* genomes.txt: metaDb - the path to an optional tagStorm file that has the metadata for each track. Each track with metadata should have a "meta" tag specified in the trackDb stanza for that track and a "meta" tag in the tagStorm file.

* Frequency: see [Update bedRMod specs #167](https://github.com/dieterich-lab/scimodom/issues/167).

* Score: models allow for `score: NonNegativInt` whereas it should be `score: PositiveInt`, but since we need to read the current
bed files (1.8), we have to allow score = 0, see also [Update bedRMod specs #167](https://github.com/dieterich-lab/scimodom/issues/167).

* Do we need all three `noScoreFilter on`, `useScore 0` (deprecated?), `spectrum off`...?

* Use bedmethyl default with missing fields?

* Add for each track `nameOfTrack.html` in the same directory as the trackDb matching the name of the track (html file does not need to be declared), see [TrackSettings](https://genome.ucsc.edu/goldenpath/help/trackDb/trackDbHub.html#bigBed_-_Item_or_Region_Track_Settings) and [templatePage](https://genome.ucsc.edu/goldenpath/help/examples/hubExamples/templatePage.html).

* Do we need `tableBrowser on` ?

* [Metadata](https://genome.ucsc.edu/goldenPath/help/metadata.html)

* Model serialization *e.g.*

```python
class UserModel(BaseModel):
    username: str
    password: str
    @model_serializer(mode='plain')
    def serialize_model(self) -> str:
        attrs = [self.username, self.password]
        return "\n".join(attrs).rstrip() + "\n"
```

## How to report issues

For bugs, issues, or feature requests, use the [bug tracker](https://github.com/eboileau/scimodhub/issues). Follow the instructions and guidelines given in the templates.

## License

The MIT License (MIT). Copyright (c) 2026 Etienne Boileau.
