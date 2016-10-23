from Config import *
import os
import csv
import logging
from vector_gen import pdb_container,fake_pdb_container
import time
from functools import wraps
import collections

#This part is used to set debug log
#This will generate a log that record every content logged with a specific security levels
fileHandler = logging.FileHandler('debug.log',mode='w')
fileHandler.setLevel(logging.DEBUG)
formatter = logging.Formatter('LINE %(lineno)-4d  %(levelname)-8s %(message)s', '%m-%d %H:%M')
fileHandler.setFormatter(formatter)
logging.getLogger('').addHandler(fileHandler)


def initiate_report():
    csv_name = 'report.csv'
    writer = file(csv_name, 'wb')
    w = csv.writer(writer)
    w.writerow(['filename','pdb Name','molecules','paired','bad_one','pairtimes'])
    return csv_name
def fn_timer(function):
    '''
    This is the decorator used for time counting issue
    Need not understand this one. It has nothing to do with generating files
    :param function:
    :return: no return. just print and record the time the decorated program ran.
    '''
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print ("Total time running %s: %s seconds" %
               (function.func_name, str(t1 - t0))
               )
        logging.warning ("Total time running %s: %s seconds" %
               (function.func_name, str(t1 - t0))
               )
        return result

    return function_timer


def generate_comment_line(src_dict):
    comment = '{'
    for k, v in src_dict.items():
        k_bundle = ''
        if isinstance(v, list):
            # print k,v
            for item in list(set(v)):
                # print item
                if len(k_bundle) == 0:
                    k_bundle += str(item)
                else:
                    k_bundle += '|' + str(item)

            # print k_bundle

            comment = comment + '_{' + k + ':' + k_bundle +'}'
        elif isinstance(v, dict):
            comment += generate_comment_line(v)
        else:
            comment = comment + '_{' + k + ':' + str(v) + '}'
    return comment+'}'

def bundle_result_mol2_file(source_mol_file ,experimentaldict, pdbdict):
    '''
    
    :param source_mol_file:
    :param experimentaldict:
    :param pdbdict:
    :return:
    '''
    assert os.path.exists(source_mol_file)
    filename = source_mol_file.split('/')[-1]

    real_dir= os.path.join(result_PREFIX,filename)

    # first deal with experimental data
    comment = 'Remark: '
    if experimentaldict is not None:
        #print experimentaldict
        comment += generate_comment_line(experimentaldict)
    #print pdbdict
    if pdbdict is not None:
        comment += generate_comment_line(pdbdict)

    with open(real_dir,'wb') as w:
        w.write('# '+comment+'\n')
        with open(source_mol_file,'rb') as o:
            w.writelines(o.read())

    print '{} is moved into the result file with addtional info in first line.'.format(filename)



@fn_timer
def bindingDB_pdb_tar_generator(src,filepos,statistic_csv=None,CLEAN=False,fileforbabel='a.sdf'):
    '''

    :param src: pdb name
    :param statistic_csv: the report csv file's name
    :param CLEAN: Wipe temporary pdb files or not. Note I will not give options to wipe results. That's dangerous
    :return: True: If everything works fine
             False: Unexpected error happens. Note if there is no reuslt, it will return True because everything runs fine.
    '''

    # write the result

    result_file_name = 'filter_{}'.format(src.split('/')[-1].split('.')[0]) + '.csv'
    filedir = os.path.join(result_PREFIX, result_file_name)
    if not os.path.isfile(filedir):
        if not os.path.exists(result_PREFIX):
            os.mkdir(result_PREFIX)

    # in case for overwriting
    '''
    if os.path.exists(filedir):
        print '{} already done.'.format(src)
        logging.info('{} already done'.format(src))
        return True
    '''

    # combine as file direction
    sdfone = filedir_PREFIX + src.upper() + '.sdf'

    # open the source molecule files
    # Naming format [PDB name].sdf all lowercase
    try:
        input_sdf = open(sdfone, 'r')
    except:
        logging.error('PDB {} with ligands sdf not found!'.format(src))
        return False

    # This variables are used for counting and statistic issue.
    active_count = 0
    count = 0
    bad_one = 0

    # csv writer
    writer = file(filedir, 'w')
    w = csv.writer(writer)
    w.writerow(experiment_part + PDB_part)

    # Combine as pdb file address
    # We generate a class to store each ligands as a dict, and use a method
    # to find the similar ones by tanimoto comparing scores to specific input files
    #PDBindex = pdb_container(src, filepos=filepos, BOX=21, Size=0.35)
    PDBindex = pdb_container(src, filepos=filepos)
    index= 0

    if PDBindex.get_pdb_type() != 'Protein':
        return False
    # In each time
    # We write one single molecule in to a sdf file called a.sdf
    # Then use this file to compare with the one we extract from pdb files
    # Since we use scripts so I just extract them to make sure that is what
    # we really want to compare
    # (But there should be a smarter way to do so)

    Comment= {}
    for Id in PDBindex.list_ResId():
        Comment[Id]=collections.OrderedDict()
        for k in experiment_part:
            Comment[Id][k]=[]
    #print  Comment
    try:
        mol = ''
        Wait_Signal = 0
        FIRST_LINE = False
        experiment_dict= {} # print 'here'
        for line in input_sdf:
            mol += line

            if FIRST_LINE==False:
                x = line.lstrip(' ').rstrip('\n').rstrip(' ')
                experiment_dict['NAME']=x
                FIRST_LINE= True

            # just lazy
            if Wait_Signal > 0:
                experiment_dict[line_key]=line.lstrip(' ').rstrip('\n').rstrip(' ')
                Wait_Signal = 0

            for i in range(len(key)):
                if key[i] in line:
                    Wait_Signal = 1
                    line_key = key[i]
                    break


            if '$$$$' in line:
                # end of a molecule
                fileforbabel = temp_pdb_PREFIX + '/{}/{}_{}.sdf'.format(src, src, index)
                o = open(fileforbabel, "w")
                o.write(mol)
                o.close()
                index+=1
                # Find pairs with at least 85% similarity scores
                ans_list = PDBindex.find_similar_target(fileforbabel)
                if len(ans_list)==0:
                    bad_one+=1
                active_count+=len(ans_list)
                for dict in ans_list:
                    #merge comment about experimental data here:
                    Id = dict['id']
                    PDBindex.bundle_autodock_file(Id)
                    for k,v in experiment_dict.items():
                        vv= v.lstrip(' ').rstrip(' ')
                        #print k,vv
                        if len(vv)>0:
                            Comment[Id][k].append(vv)

                mol = ''
                FIRST_LINE=False
                experiment_dict={}



        for k in PDBindex.list_ResId():
            # print k,v
            ligand_dict= PDBindex.heterodict[k]
            assert 'file_generated' in ligand_dict
            if ligand_dict['file_generated']==True:
                bundle_result_mol2_file(ligand_dict['filename'][:-4]+'.mol',Comment[k],PDBindex.bundle_result_dict(k))
                #generate one_line in csv files
                one_line= [''] * len(experiment_part)
                i= 0
                for kk,v in Comment[k].items():
                    k_bundle= ''
                    assert isinstance(v,list)
                    for item in list(set(v)):
                        if len(k_bundle)==0:
                            k_bundle+=str(item)
                        else:
                            k_bundle+='|'+str(item)
                    one_line[i]= k_bundle
                    i+=1
                w.writerow(one_line+PDBindex.bundle_result(k))

    except:
        #raise TypeError
        logging.error('Unknown error here!')
        return False
    logging.warning('{} bad ligands found'.format(bad_one))
    logging.warning('{} molecules are detected, and {} pairs are recorded.'.format(index, active_count))

    # Discard unused one
    #PDBindex.clean_temp_data()

    # Do some record
    if statistic_csv is not None:
        writer = file(statistic_csv, 'ab')
        w = csv.writer(writer)
        w.writerow([src, count, count - bad_one, bad_one, active_count])
        writer.flush()
        writer.close()

    # Wipe the pdb temporary files if you wish:
    if CLEAN:
        files = os.path.join(temp_pdb_PREFIX,src)
        os.system('rm -r ' + files)

    return True


@fn_timer
def docking_mol2_generator(pdbname,docking_ligand_file,pdb_filepos=None,benchmark_file=None,suffix=None):
    '''

    :param pdbname:
    :param docking_ligand_file:
    :param pdb_filepos:
    :param benchmark_file:
    :param suffix:
    :return:
    '''
    if pdb_filepos is None:
        pdb_filepos= os.path.join(pdb_PREFIX,pdb+'.pdb.gz')

    A = pdb_container('1avd', filepos='/media/wy/data/pdb_raw/1avd.pdb.gz')
    A.add_ligands('/media/wy/data/fast/1avd/1avd_248_ligand.mol2', suffix='fast',
                  benchmark_file='/media/wy/data/fast/1avd/example.pdb')


if __name__ == '__main__':


    for pdb in PDB_tar[0:1]:
        pdb=pdb.lower()
        filepath= os.path.join(pdb_PREFIX,pdb+'.pdb.gz')
        bindingDB_pdb_tar_generator(pdb,filepath,statistic_csv='report.csv',CLEAN=True)