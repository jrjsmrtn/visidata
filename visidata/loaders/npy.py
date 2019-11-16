from visidata import *

'Loaders for .npy and .npz.  Save to .npy.  Depends on the zip loader.'

class NpySheet(Sheet):
    def iterload(self):
        import numpy
        if not hasattr(self, 'npy'):
            self.npy = numpy.load(str(self.source), encoding='bytes')
        self.reloadCols()
        yield from Progress(self.npy, total=len(self.npy))

    def reloadCols(self):
        self.columns = []
        for i, (name, fmt, *shape) in enumerate(self.npy.dtype.descr):
            if shape:
                t = anytype
            elif 'M' in fmt:
                self.addColumn(Column(name, type=date, getter=lambda c,r,i=i: str(r[i])))
                continue
            elif 'i' in fmt:
                t = int
            elif 'f' in fmt:
                t = float
            else:
                t = anytype
            self.addColumn(ColumnItem(name, i, type=t))


class NpzSheet(ZipSheet):
    # rowdef: tuple(tablename, table)
    columns = [
        ColumnItem('name', 0),
        ColumnItem('length', 1, type=vlen),
    ]

    def iterload(self):
        import numpy
        self.npz = numpy.load(str(self.source), encoding='bytes')
        yield from Progress(self.npz.items())

    def openRow(self, row):
        import numpy
        tablename, tbl = row
        if isinstance(tbl, numpy.ndarray):
            return NpySheet(tablename, npy=tbl)

        return load_pyobj(tablename, tbl)


@Sheet.api
def save_npy(sheet, p):
    import numpy as np

    dtype = []

    for col in Progress(sheet.visibleCols):
        if col.type in (int, vlen):
            dt = 'i8'
        elif col.type in (float, currency):
            dt = 'f8'
        elif col.type is date:
            dt = 'datetime64[s]'

        else: #  if col.type in (str, anytype):
            width = col.getMaxWidth(sheet.rows)
            dt = 'U'+str(width)
        dtype.append((col.name, dt))

    data = []
    for row in sheet.itervalues():
        nprow = []
        for col, val in row:
            val = col.getTypedValue(row)
            if isinstance(val, TypedWrapper):
                if col.type is anytype:
                    val = ''
                else:
                    val = col.type()
            elif col.type is date:
                val = np.datetime64(val.isoformat())
            nprow.append(val)
        data.append(tuple(nprow))

    arr = np.array(data, dtype=dtype)
    with p.open_bytes(mode='w') as outf:
        np.save(outf, arr, allow_pickle=False)


vd.filetype('npy', NpySheet)
vd.filetype('npz', NpzSheet)
