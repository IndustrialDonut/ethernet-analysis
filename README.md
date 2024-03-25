# ethernet-analysis
Using Python to decode real ethernet frames captured from oscilloscope

## Main notebook 'ethernet_auto.ipynb'
Open it up and it should just run, assuming you have the python dependencies like crcmod, pandas, matplotlib.
There are sample waveform captures in the ethernet_captures/ folder, any of these can be loaded in the main notebook by passing the file name to the get_capture() method. Some of them may need to be inverted. To tell if a waveform needs to be inverted, check to confirm that the graph shows the first activity going NEGATIVE before rising positive. This is because ethernet starts the preamble with 10101010, and it swings negative before positive to have a complete transition from low to high instead of just 0 to high.
