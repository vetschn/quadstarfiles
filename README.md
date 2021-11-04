# quadstarfiles

This little package parses and converts `.sac` files from Pfeiffer's Quadstar 32-bit (QMS 422 & QMS 400 Quadrupole Mass Spectrometers) into Pandas DataFrames, Excel files and CSV files.

There is a quirk in Quadstar 32-bit's *Dispsav* utility: The program does not allow you to write multiple/all cycles stored in a `.sac` file as human-readable ASCII. Instead you have to select one cycle after the other. With this parser/converter you can export all cycles stored in an `.sac` in one go.

```bash
> cd ./quadstarfiles
> pip install .
```

## Example Usage

### `parse`

Parse the data as it is stored in the corresponding file. The method automatically determines filetype and tries to apply the respective parser.

```python
>>> import quadstarfiles as qsf
>>> qsf.parse("./sac_files/airdemo.sac")
```


### `to_df`

Parse the file and transform only the data part into a Pandas `DataFrame`. 

```python
>>> import quadstarfiles as qsf
>>> qsf.to_df("./sac_files/airdemo.sac")
```


### `to_csv`

Parse the file and write the data part into a `.csv` file.

```python
>>> import quadstarfiles as qsf
>>> qsf.to_csv("./sac_files/airdemo.sac")
```


### `to_xlsx`

Parse the file and write the data part into an Excel `.xlsx` file.

```python
>>> import quadstarfiles as qsf
>>> qsf.to_xlsx("./sac_files/airdemo.sac")
```
