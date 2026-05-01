path = r'c:/Users/koold/Desktop/EGON/KOOL_TPV_V2/kool_tpv/modulos/tpv/subviews/stock_subview.py'
with open(path, 'rb') as f:
    data = f.read().splitlines()
for i in range(220, 260):
    if i-1 < len(data):
        print(f"{i}: {data[i-1]!r}")
