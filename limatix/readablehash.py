vowels="AEIOUY"
nonvowels="BCDFGHJKLMNPQRSTVWXZ"

orders=[
    (13, 25, 24,  4,  8, 20, 14, 11,  5, 22, 19, 15,  0, 23, 18, 16, 12, 3,  6, 17, 21,  2, 10,  1,  7,  9), # 1 copy for vowelneed=0
    (28, 31,  0, 22,  2,  5, 15, 29, 19, 16,  4, 17, 24, 11, 25, 18, 13,
        8,  1,  3, 10, 27,  6, 20, 21, 26, 23, 14,  7, 12, 30,  9),  # 2 copies for vowelneed=1
    (35, 14, 29, 19, 27, 13,  0, 42,  4, 38, 43, 41, 34, 28, 21, 22, 15,
       37, 32, 33, 12,  5, 24, 20, 18, 23,  3,  8, 30, 11, 17,  7, 16, 10,
        2,  9, 40, 25, 36,  1,  6, 39, 31, 26), # four copies for vowelneed = 2
    ( 14, 62, 47, 27, 26,  8, 66, 30, 11, 67, 52,  4, 37, 61, 51, 22, 39,
       58, 59, 31, 23, 15, 29, 46, 17, 36, 13, 48, 43,  2, 53,  9, 24, 49,
       33,  7,  5, 60,  0, 28, 65, 42, 34,  6, 45, 56,  3, 54, 18, 57, 21,
       20, 32, 44, 10, 50, 12, 41, 38,  1, 35, 25, 55, 63, 40, 64, 19, 16), # eight copies for vowelneed=3
    ]

def readablehash(inp):
    pyhash=hash(inp)

    # print ("%x" % pyhash)

    outstr=""
    numvowels=0
    numconsts=0
    vowelneed=0

    while len(outstr) < 8 and numconsts < 5:

        bits=pyhash & ((1<<6)-1) # 63 -- i.e. 6 bits
        pyhash >>= 6
        
        seekstr=vowels*(2**vowelneed)+nonvowels
        order=orders[vowelneed]
        # print len(order)
        # print len(seekstr)
        assert(len(order)==len(seekstr))
        
        bitsval=bits % len(order)
        
        # print "%x %x %d" % (bits,bitsval,bitsval)

        char=seekstr[order[bitsval]]

        outstr+=char
        
        if char in vowels: 
            numvowels+=1
            vowelneed=0
            pass
        else :
            numconsts+=1
            vowelneed += 1
            if vowelneed > 3: 
                vowelneed=3
                pass
            pass
        
        pass
    return outstr
