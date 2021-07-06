import sys, json, subprocess, shlex, csv, argparse

#Function to get disks json from source vm name
def get_disk_source(srczone,vmname):
    disklist_command = "gcloud compute instances describe --zone=" + srczone + " " + vmname + " --format="'json(disks)'""
    disklist_output = subprocess.check_output(shlex.split(disklist_command))
    disklist_output_json = json.loads(disklist_output)
    return disklist_output_json

#Class to create diskname and snapshot name map
class SnapshotData:
    def __init__(self,disktype,diskboot,snapurl_output):
        self.disktype = disktype 
        self.diskboot = diskboot
        self.snapurl_output = snapurl_output 

#Function to get disk name, boot disk(True/False) and snapshot URL from specific date
def get_disk_name_type_snap_details():
    diskdict = {}
    disklist_output_json = get_disk_source(srczone=srczone,vmname=vmname)
    for disklist_row in disklist_output_json["disks"]:
        
        #Fetch if boot disk
        diskboot = disklist_row["boot"]

        #Fetch disk type
        disksource = disklist_row["source"]
        diskname_command = "gcloud compute disks describe " + disksource + " --format=json"
        diskname_output = subprocess.check_output(shlex.split(diskname_command))
        diskname_output_json = json.loads(diskname_output)
        disktype = diskname_output_json['type'].rsplit('/',1)[1]
        
        #Fetch snapshot name from date
        snapname_command = 'gcloud compute snapshots list --limit=1 --filter="(sourceDisk ~ ' + disksource + '$) \
            AND (creationTimestamp.date("%Y-%m-%d", Z)="' + snapdate + '")" --sort-by="~creationTimestamp" --format="value(name)"'
        snapname_output = subprocess.check_output(shlex.split(snapname_command), universal_newlines=True)
        
        if(snapname_output==''):
            print('\u001b[31;1m\nNo snapshots found for selected date ' + snapdate + '\u001b[0m')
            snapurl_output = ''
        else:
        #Fetch snapshot URL from snapshot name
            snapurl_command = 'gcloud compute snapshots describe ' + snapname_output.strip("\n") + ' --format="value(selfLink)"'
            snapurl_out = subprocess.check_output(shlex.split(snapurl_command), universal_newlines=True)
            snapurl_output = (snapurl_out).strip("\n")

        #Create object to return disktype and snapshot URL
        obj = SnapshotData(disktype,diskboot,snapurl_output)
        diskdict[diskname_output_json['name']] = obj
    return diskdict

#Function to create target disk and vm names based on scenario
def get_tgt_name(action,srcname):
    if(action == '1'):
        tgtname = srcname + '-bubble-dr'
    elif(action == '2'):
        tgtname = srcname + '-dr'
    elif(action == '3'):
        if(srcname.endswith('-dr')):
            tgtname = srcname.replace('-dr','')
        else:
            tgtname = srcname
    else:
        action = input('\u001b[31;1mIncorrect input provided. Please select [1/2/3]!\nPlease confirm if activity is Bubble DR [1] / Failover [2] / Failback [3] : \u001b[0m')
        get_tgt_name(action=action,srcname=srcname)
    return tgtname

#Function to get hostname of source VM
def get_vm_hostname(srczone,vmname):
    hostname_command = 'gcloud compute instances describe --zone=' + srczone + ' ' + vmname + ' --format="value(hostname)"'
    hostname_execute = subprocess.check_output(shlex.split(hostname_command), universal_newlines=True)
    hostname = hostname_execute.strip("\n")
    return hostname

#Function to get network tag of source VM
def get_vm_nw_tags(srczone,vmname):
    nw_tag_command = 'gcloud compute instances describe --zone=' + srczone + ' ' + vmname + ' --format="value(tags.items)"'
    nw_tag_output = subprocess.check_output(shlex.split(nw_tag_command), universal_newlines=True)
    nw_tag_list = nw_tag_output.split(';')
    return nw_tag_list

#Function to add NW tags
def add_nw_tags(tgtvmname,tgtprojid,tgtzone,tag):
    nw_tag_add_command = 'gcloud compute instances add-tags ' + tgtvmname + ' --project ' + tgtprojid + \
        ' --zone=' + tgtzone + ' --tags=' + tag
    subprocess.run(shlex.split(nw_tag_add_command))

#Function to get machine type of source VM
def get_vm_type(srczone,vmname):
    vm_type_command = 'gcloud compute instances describe --zone=' + srczone + ' ' + vmname + ' --format="value(machineType)"'
    vm_type_output = subprocess.check_output(shlex.split(vm_type_command), universal_newlines=True)
    vm_type = vm_type_output.rsplit('/',1)[1]
    return vm_type

#Function to get VM labels
def get_vm_labels(srczone,vmname):
    vm_label_list_command = 'gcloud compute instances describe --zone=' + srczone + ' ' + vmname + ' --format="value(labels)"'
    vm_label_list_output = subprocess.check_output(shlex.split(vm_label_list_command), universal_newlines=True)
    vm_label_list = vm_label_list_output.split(';')
    return vm_label_list

#Function to add VM labels
def add_vm_labels(tgtvmname,tgtprojid,tgtzone,label):
    vm_label_add_command = 'gcloud compute instances add-labels ' + tgtvmname + ' --project ' + tgtprojid + \
        ' --zone=' + tgtzone + ' --labels=' + label
    subprocess.run(shlex.split(vm_label_add_command))

#Function to get subnet URL based on target subnet name from csv file. URL is needed for VM creation.
def get_snet_detail(tgtsnet,nwhostproj,tgtregion):
    snet_command = 'gcloud compute networks subnets describe ' + tgtsnet + ' --project=' + nwhostproj + ' --region=' + tgtregion + ' --format="value(selfLink)"'
    tgtsubnet = subprocess.check_output(shlex.split(snet_command), universal_newlines=True)
    return tgtsubnet

#Function to create target disks
def create_tgt_disks(tgtdiskname,tgtprojid,srcsnapurl,tgtdisktype,tgtzone):
    diskcreate_command = "gcloud compute disks create " + tgtdiskname + " --project " + tgtprojid \
            + " --source-snapshot " + srcsnapurl + " --type " + tgtdisktype + " --zone=" + tgtzone 
    subprocess.run(shlex.split(diskcreate_command))

#Function to attach target data disks
def attach_tgt_disks(tgtprojid,tgtvmname,tgtdisk,tgtzone):
    diskattach_command = 'gcloud compute instances --project ' + tgtprojid + \
        ' attach-disk ' + tgtvmname + ' --disk ' + tgtdisk + ' --zone=' + tgtzone
    subprocess.run(shlex.split(diskattach_command))

#Function to create target VM
def create_tgt_vm(tgtprojid,tgtvmname,vmname,srczone,bootdiskname,tgtsnet,nwhostproj,tgtregion,tgtipaddr,tgtzone):
    hostname = get_vm_hostname(srczone=srczone,vmname=vmname)
    tgtsubnet = get_snet_detail(tgtsnet=tgtsnet,nwhostproj=nwhostproj,tgtregion=tgtregion)
    vm_type = get_vm_type(srczone=srczone,vmname=vmname)
    vmcreate_command = "gcloud compute instances create --project " + tgtprojid + " " + tgtvmname + \
                               " --hostname=" + hostname + " --disk=name=" + bootdiskname + \
                               ",device-name="+ bootdiskname + ",mode=rw,boot=yes" + \
                               " --subnet=" + tgtsubnet + " --private-network-ip=" + tgtipaddr + \
                               " --network-tier=STANDARD --machine-type=" + vm_type + \
                               " --no-require-csek-key-create --zone=" + tgtzone + " --no-address"
    try:
        subprocess.check_output(shlex.split(vmcreate_command))
    except:
        print('\u001b[31;1m\nError while creating VM\u001b[0m')

##-------Take User Inputs----------

#srcprojid = input('Please enter source project id : ')
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-csv","--csvfilename", help="enter path to csv file", type=str)
parser.add_argument("-tr","--targetregion", help="enter target region", type=str)
parser.add_argument("-tp","--targetprojectid", help="enter target project id", type=str)
parser.add_argument("-np","--nwhostproject", help="enter network host project id", type=str)
parser.add_argument("-sz","--sourcezone", help="enter target region", type=str)
parser.add_argument("-tz","--targetzone", help="enter target region", type=str)
if len(sys.argv)<13:
        parser.print_help()
        sys.exit(1)
args = parser.parse_args()
csvname = args.csvfilename
nwhostproj = args.nwhostproject
tgtregion = args.targetregion
tgtprojid = args.targetprojectid
srczone = args.sourcezone
tgtzone = args.targetzone

date = input('\nPlease enter snapshot date(YYYY-MM-DD): ')
snapdate = str(date)
action = input('Please confirm if activity is Bubble DR [1] / Failover [2] / Failback [3] : ')

#Read inputs from csv file
with open(csvname, 'r') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=',')
    for line in reader:
        vmname = line["VM Name"],
        vmname = (str(vmname[0]))
        tgtsnet = str(line["Target Subnet"])
        tgtipaddr = str(line["Target IP address"])
##-------Fetch Disk details-------
        print('\n*******************************************************************************')
        print('\u001b[34;1mFetching disk names & snapshot details for VM ' + vmname + ' .....\u001b[0m')
        print('*******************************************************************************')
        disk_name_map = get_disk_name_type_snap_details()
        datadisks = []
        for disk in disk_name_map:
            
            #Execute function and class to get disktype and snapshot url
            obj = disk_name_map[disk]
            tgtdiskname = get_tgt_name(action=action,srcname=disk)
            tgtdisktype = obj.disktype
            srcsnapurl = obj.snapurl_output

            #Create target disk
            print('\u001b[34;1m\nCreating disk for source disk ' + disk + '\u001b[0m')
            print('---------------------------------------------------------------------')
            create_tgt_disks(tgtdiskname=tgtdiskname,tgtprojid=tgtprojid,srcsnapurl=srcsnapurl,tgtdisktype=tgtdisktype,tgtzone=tgtzone)
            
            #Identify bootdisk based on disk parameter boot = True from map. Create list for other disks.
            if(obj.diskboot):
                bootdiskname = tgtdiskname
            else:
                datadisks.append(tgtdiskname)
        
        #Create target VMs
        tgtvmname = get_tgt_name(action=action,srcname=vmname)
        print('\u001b[34;1m\nCreating target VM ' + tgtvmname + '\u001b[0m')
        print('------------------------------------------------------------')
        create_tgt_vm(tgtprojid=tgtprojid,tgtvmname=tgtvmname,vmname=vmname,srczone=srczone,bootdiskname=bootdiskname,\
            tgtsnet=tgtsnet,nwhostproj=nwhostproj,tgtregion=tgtregion,tgtipaddr=tgtipaddr,tgtzone=tgtzone)

        #Attach disks to VM
        print('\u001b[34;1m\nAttaching data disks to VM ' + tgtvmname + '\u001b[0m')
        print('------------------------------------------------------------')
        for disk in datadisks:
            attach_tgt_disks(tgtprojid=tgtprojid,tgtvmname=tgtvmname,tgtdisk=disk,tgtzone=tgtzone)

        #Add NW tags
        print('\u001b[34;1m\nAdding network tags to VM ' + tgtvmname + '\u001b[0m')
        print('------------------------------------------------------------')
        nw_tag_list = get_vm_nw_tags(srczone=srczone,vmname=vmname)
        for tag in nw_tag_list:
            add_nw_tags(tgtvmname=tgtvmname,tgtprojid=tgtprojid,tgtzone=tgtzone,tag=tag)

        #Add VM labels
        print('\u001b[34;1m\nAdding VM labels to VM ' + tgtvmname + '\u001b[0m')
        print('------------------------------------------------------------')
        vm_label_list = get_vm_labels(srczone=srczone,vmname=vmname)
        labelstring = ''
        for label in vm_label_list[:-1]:
            labelstring = labelstring + str(label) + ','
        labelstring = labelstring + vm_label_list[-1]
        add_vm_labels(tgtvmname=tgtvmname,tgtprojid=tgtprojid,tgtzone=tgtzone,label=labelstring)
        
