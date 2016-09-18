from Config import result_PREFIX
import os,io
import csv

# import in case
import pandas as pd

# Quickly merge all result files into 1 single gigantic file
Output_name= 'all.csv'

if __name__ == '__main__':

    filenames= os.listdir(result_PREFIX)

    totalfile = file(os.path.join(result_PREFIX,Output_name),'wb')
    out = csv.writer(totalfile)

    Never_OUTPUT= True
    count = 0
    lines =0

    # write legal files
    for filedir in filenames:
        if filedir== Output_name or filedir.split('.')[-1]!='csv':
            continue

        # csv writer
        csvfile= file(os.path.join(result_PREFIX,filedir),'rb')
        o = csv.reader(csvfile)

        for line in o:
            if line[0]=='Name':
                if Never_OUTPUT:
                    out.writerow(line)
                    Never_OUTPUT= False
                continue
            out.writerow(line)
            lines+=1

        count+=1
        print 'Successfully merge {}'.format(filedir)
        out.flush()
        csvfile.close()

    print '{} files and {} lines are merged into one called {}'.format(count,lines,Output_name)
    totalfile.close()