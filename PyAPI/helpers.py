def scryfall_color_converter(colors):
    #this is about to get ugly but itl save time later :["B","G","R","U","W"]
    colorbase = ['0','0','0','0','0']
    for c in colors:
        if c == "B":
            colorbase[0] = '1'
        if c == "G":
            colorbase[1] = '1'
        if c == "R":
            colorbase[2] = '1'
        if c == "U":
            colorbase[3] = '1'
        if c == "W":
            colorbase[4] = '1'
    return colorbase_to_id("".join(colorbase))

def colorbase_to_id(cb):
    #becomes obsolete if ids change but just faster for rn
    if(cb == '00000'): return 1
    if(cb == '00010'): return 2
    if(cb == '00001'): return 3
    if(cb == '01000'): return 4
    if(cb == '00100'): return 5
    if(cb == '10000'): return 6

    if(cb == '00011'): return 7
    if(cb == '01001'): return 8
    if(cb == '01100'): return 9
    if(cb == '10100'): return 10
    if(cb == '10010'): return 11
    if(cb == '00101'): return 12
    if(cb == '11000'): return 13
    if(cb == '00110'): return 14
    if(cb == '10001'): return 15
    if(cb == '01010'): return 16
    
    if(cb == '01011'): return 17
    if(cb == '11001'): return 18
    if(cb == '10011'): return 19
    if(cb == '10110'): return 20
    if(cb == '00111'): return 21
    if(cb == '11100'): return 22
    if(cb == '10101'): return 23
    if(cb == '01101'): return 24
    if(cb == '11010'): return 25
    if(cb == '01110'): return 26

    if(cb == '11110'): return 27
    if(cb == '11101'): return 28
    if(cb == '01111'): return 29
    if(cb == '11011'): return 30
    if(cb == '10111'): return 31
    if(cb == '11111'): return 32
