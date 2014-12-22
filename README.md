pyhts
=====
A script wrapper to easily adapt hts to common needs. The core is provided in python.

# Example
```bash
python3 synthesis/synth.py -v -c config/example_config.json -m ~/work/tools/hts_gradle/build/raw/models/re_clustered_cmp.mmf \
          -d ~/work/tools/hts_gradle/build/raw/models/re_clustered_dur.mmf \
          -t ~/work/tools/hts_gradle/build/raw/trees/ -u ~/work/tools/hts_gradle/build/raw/trees \
          -g ~/work/tools/hts_gradle/build/raw/gv \
          -i ~/work/corpus/arctic_partial/labels/gen/alice01.lab -p 0 \
          -l ~/work/corpus/arctic_partial/lists/full.list -o test
```
