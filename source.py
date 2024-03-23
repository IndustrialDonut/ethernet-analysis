import pandas as pd
import re
import os


def clamp(val, minval=-1, maxval=1):
    if val < minval: return minval
    if val > maxval: return maxval
    return val


# Auto parse bitstream, parse the WAVEFORM to generate a bit-string

def sign(x):
    if x < 0: return -1
    if x > 0: return 1
    return 0

# Assume all edge transitions are 'clean', NO bouncing back once the voltage crosses 0
def edge(last, new):
    return sign(last) != sign(new)

def parse_manchester(v_series, ethernet_signal_T=1/10E6, wave_sample_T=1E-9):

    """Take voltage timeseries and return df of 1's and 0's per Manchester encoding (include preamble and SFD, entire transmission).
    Must provide the ethernet signalling period (T) and the oscilloscope/waveform sample period in seconds."""

    # Threshold of time we must pass from the last edge/bit to the next, so that we don't measure the intermediate 
    # edges that occur in Manchester encoding.
    thrsh = ethernet_signal_T * 0.7

    # initialize the mutables for iteration
    result = pd.Series()
    t = 0.0
    efd_t = 0.0 # end of frame delimeter... just when signal goes high for more than a full clock period
    last_v = -1
    for i, v in v_series.items():
        t += wave_sample_T # 1GHz from my Rigol oscilloscope
        efd_t += wave_sample_T
        if efd_t > (ethernet_signal_T * 1.5) and len(result) > 5:
            break
        
        # if we have passed half the signalling period... now we look for the 'real' edge
        # not just the intermediate edge if there was one, for manchester encoding.
        if t >= thrsh:
            if edge(last_v, v):
                t = 0.0
                efd_t = 0.0

                if sign(v) == 1:
                    result[i] = '1'
                else:
                    result[i] = '0'
                    
        last_v = v
    
    df = result.reset_index()
    df.columns = ['t', 'Q']
    return df


def ffill_Q_index(bit_df, v_series):
    # q index / bit index is n
    
    df = bit_df.reset_index().set_index('t')
    df.columns = ['n', 'Q']
    df = v_series.to_frame().join(df, how='left')
    df.n = df.n.ffill(limit=125) # this is so that shading the FCS doesn't shade to the end of the entire graph..
    df.n = df.n.fillna(-1)
    df.n = df.n.astype(int)
    #t.Q = t.Q.ffill()
    return df


# Functions to parse the bit-string per ethernet spec

def chunk_octets(bits):
    n_bits = len(bits)
    n_octets = n_bits//8
    if (n_bits % 8) != 0:
        raise Exception("input bits are not a multiple of 8")
    chunked = [bits[(i*8):(i*8)+8] for i in range(n_octets)]
    #logger.info(f"{n_octets} octets chunked")
    return chunked

def reverse_string(s):
    a = [s[len(s) - i - 1] for i in range(len(s))]
    flipped = ''.join(a)
    return flipped

def reverse_octets(a):
    return [reverse_string(octet) for octet in a]

# Hexify a single byte (pad=2)
def hexify(x, pad=2):
    return hex(int(x, base=2))[2:].rjust(pad, '0')

def macify(a):
    resNums = [hexify(x) for x in a]
    r = ':'.join(resNums)
    return r


def find_end_of_preamble(rawbits):
    """Take the rawbits and return the index of the bit which is the start of the destination mac address (end of SFD + 1).
    While my parsing script is simple, it might not capture the start of / full preamble accurately.
    Thereofore, instead of searching for the full preamble + SFD, we just look for 
    'a large portion of the preamble' which is 5 bytes of 01010101 and then the SFD, not caring what came at the very start.
    We take this to determine the starting bit index of the DEST MAC which we will call the start of the ethernet frame.
    """
    sfd = '10101011'
    psuedo_preamble='.*'+'10101010'*5 + sfd
    r = re.search(psuedo_preamble, rawbits)
    dest_mac_start = len(r.group(0))
    return dest_mac_start


# prepare for various ipv4 payload types
def load_icmp_types():
    icmp_types = pd.read_csv('icmp-parameters-types.csv')
    return icmp_types

# get icmp codes per message type and concat together
def load_icmp_codes():
    dfs = []
    for file in os.listdir('icmp_codes'):
        path = os.path.join('icmp_codes', file)
        type_ = re.match('.*(\d)\.csv', file).group(1)
        df = pd.read_csv(path)
        df['Type'] = type_
        dfs.append(df)

    icmp_codes = pd.concat(dfs)
    icmp_codes = icmp_codes.drop(columns='Value').dropna(subset='Codes').sort_values('Type')
    return icmp_codes

