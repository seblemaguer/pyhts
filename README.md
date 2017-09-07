# python HTS wrapper (pyHTS)

This set of scripts aims to easily use HTS to achieve synthesis. It currently supports:
  - Modeling:
      - HMM
      - DNN using tensorflow
  - Vocoder
      - STRAIGHT

It is also possible to impose the different kind of coefficients (F0, MGC, BAP).
In case of the F0, it is also possible to impose an interpolated one.
In this case, the voicing decision is achieved by using the mask produced by HTS

## Command line

```bash
synth.py [-h] [-v] (--config=CONFIG) [--input_is_list] [--pg_type=PG_TYPE]
                   [--nb_proc=NB_PROC] [--preserve] [--imposed_duration]
                   [--renderer RENDERER] [--generator GENERATOR]
                   [--impose_f0_dir=F0] [--impose_mgc_dir=MGC] [--impose_bap_dir=BAP]
                   [--impose_interpolated_f0_dir=INT_F0]
                   <input> <output>

Arguments:
  input                                           the input file (label by default but can be a list of files)
  output                                          the output directory

Options:
  -h --help                                       Show this help message and exit.
  -v --verbose                                    Verbose output.
  -c CONFIG --config=CONFIG                       Configuration file.
  -s --input_is_list                              the input is a scp formatted file.
  -p PG_TYPE --pg_type=PG_TYPE                    parameter generation type [default: 0].
  -P NB_PROC --nb_proc=NB_PROC                    Activate parallel mode [default: 1].
  -r --preserve                                   not delete the intermediate and temporary files.
  -D --imposed_duration                           imposing the duration at a phone level.
  -R RENDERER --renderer=RENDERER                 override the renderer
  -G GENERATOR --generator=GENERATOR              override the generator
  -M MGC --impose_mgc_dir=MGC                     MGC directory to use at the synthesis level.
  -B BAP --impose_bap_dir=BAP                     BAP directory to use at the synthesis level.
  -F F0 --impose_f0_dir=F0                        F0 directory to use at the synthesis level.
  -I INT_F0 --impose_interpolated_f0_dir=INT_F0   interpolated F0 directory to use at the synthesis level.
```

## TODO

see <todo.org>
