import sys, json, subprocess, shlex, csv, argparse, datetime

#Function to get disks json from source vm name
def get_disk_source(srczone,vmname):
    disklist_command = "gcloud compute instances describe --zone=" + srczone + " " + vmname + " --format="'json(disks)'""
    disklist_output = subprocess.check_output(shlex.split(disklist_command))
    disklist_output_json = json.loads(disklist_output)
    return disklist_output_json

def create_snapshots(srczone,vmname):
    e = datetime.datetime.now()
    date = ("%s-%s-%s-%s-%s-%s" % (e.year, e.month, e.day, e.hour, e.minute, e.second))
    disklist_output_json = get_disk_source(srczone=srczone,vmname=vmname)
    for disklist_row in disklist_output_json["disks"]:
        diskname = disklist_row['source'].rsplit('/',1)[1]
        snapcreate_command = 'gcloud compute disks snapshot ' + diskname + ' --zone=' + srczone + \
            ' --snapshot-names=' + diskname + '-' + date + ' --description="Ad-hoc snapshot for ' + date + '"'
        try:
            subprocess.check_output(shlex.split(snapcreate_command))
        except Exception as err:
            print('\u001b[31;1m\nError taking snapshot for disk : ' + diskname + '\u001b[0m')

parser = argparse.ArgumentParser()
parser.add_argument("-csv","--csvfilename", help="enter path to csv file", type=str)
parser.add_argument("-sz","--sourcezone", help="enter target region", type=str)
if len(sys.argv)<5:
        parser.print_help()
        sys.exit(1)
args = parser.parse_args()
csvname = args.csvfilename
srczone = args.sourcezone

with open(csvname, 'r') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    for line in reader:
        vmname = line["VM Name"],
        vmname = (str(vmname[0]))
        print('\nPerforming snapshots of all disks for VM ' + vmname)
        create_snapshots(srczone=srczone,vmname=vmname)        
