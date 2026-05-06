# SciModHub

Sci-ModoM UCSC track hub generator. 
**scimodhub** builds a UCSC track hub for Sci-ModoM using a *faceted composite*.

- one hub with one or more organisms
- one faceted composite per organism
- one subtrack per dataset and modification
- faceting by: modification, cell type/tissue/organism, and technology (follows Sci-ModoM Search design)
- itemRgb is a blue to red gradient according to frequency (percent modified)
- score shading/filtering is turned-off at the track level (score definition/policy -> more details)
- mouseover -> default


## Documentation

### Kent binaries

Copy the application binaries

```bash
cd scripts 
./copy_ucsc_exe
```

and make them visible. Fetch chrom.sizes from Sci-ModoM, or from UCSC using the chosen assembly.
In the latter case, update the configuration file.

### Install

```bash
pip install -e .
```

### Fetch

### Build

```bash
scimodhub --config data/examples/config.yaml build  
```

## Dev. notes

* The manifest contains one row per dataset file. Required columns:

```
dataset_id
project_id
taxa_id
rna
tech
modomics_sname
cto
bedrmod_path
```

The bedRmod header is validated for EUF version and assembly; the assembly is specified in the configuration file. There is currently no API endpoint to query the Sci-ModoM assembly version.


* TrackDb shortLabel is limited to 17 printable characters. This label is a composite of 2 values given in the configuration file. If this fail with `pydantic_core._pydantic_core.ValidationError ... short_label ... String should have at most 17 characters`, change values in the configuration file.



### Questions

- Use bedmethyl default with missing fields?
- Add for each track `nameOfTrack.html` in the same directory as the trackDb matching the name of the track (html file does not need to be declared). See https://genome.ucsc.edu/goldenpath/help/trackDb/trackDbHub.html#bigBed_-_Item_or_Region_Track_Settings and https://genome.ucsc.edu/goldenpath/help/examples/hubExamples/templatePage.html
- Do we need `tableBrowser on` ?
- https://genome.ucsc.edu/goldenPath/help/metadata.html
- Try `noScoreFilter on`, `useScore 0` (deprecated?), `spectrum off`... do we need all of them? Do we need score=0? And what if score>1000?

### Todos

* *genomes.txt*: metaDb - the path to an optional tagStorm file that has the metadata for each track. Each track with metadata should have a "meta" tag specified in the trackDb stanza for that track and a "meta" tag in the tagStorm file.
* `_add_subtrack_spec`: add option (config or args) to convert modification short names to MODOMICS code for track names.
* customize *description.html*, add text to config and pass down.

* hubCheck

```
warning: missing description page for track. Add 'html SciModoM.html' line to the 'SciModoM' track stanza.
warning: missing description page for track. Add 'html SciModoM_dataset00001Y.html' line to the 'SciModoM_dataset00001Y' track stanza.
warning: missing description page for track. Add 'html SciModoM_dataset00001m6A.html' line to the 'SciModoM_dataset00001m6A' track stanza.
warning: missing description page for track. Add 'html SciModoM_dataset00002Y.html' line to the 'SciModoM_dataset00002Y' track stanza.
warning: missing description page for track. Add 'html SciModoM_dataset00003m6A.html' line to the 'SciModoM_dataset00003m6A' track stanza.
```

## Testing


## How to report issues

For bugs, issues, or feature requests, use the [bug tracker](https://github.com/eboileau/scimodhub/issues). Follow the instructions and guidelines given in the templates.

## License

The MIT License (MIT). Copyright (c) 2026 Etienne Boileau.
