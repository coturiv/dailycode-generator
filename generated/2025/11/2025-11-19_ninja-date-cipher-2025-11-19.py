# idea: ninja date cipher: 2025-11-19
# compact fallback implementation when AI code is unavailable
import math
import random

# generate an ascii mosaic using simple trigonometric patterns
def generate(n=40):
    r=[]
    t=random.Random(n)
    for i in range(n):
        line=''
        for j in range(n):
            # blend sine and cosine fields with a random perturbation
            x=math.sin(i*0.15)+math.cos(j*0.15)
            y=math.sin((i+j)*0.08)
            v=x*y+t.random()*0.5
            # map magnitude to a small palette of characters
            line+=(' .:+*#'[min(5,int(abs(v)*6))])
        r.append(line)
    sep='\n'
    return sep.join(r)

if __name__=='__main__':
    print(generate())