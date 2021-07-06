import sys, json, subprocess, shlex, csv, argparse

def get_vm_hostname(srczone,vmname,srcprojid):
    hostname_command = 'gcloud compute instances describe --zone=' + srczone + ' ' + vmname + ' --project ' + srcprojid + ' --format="value(hostname)"'
    hostname_execute = subprocess.check_output(shlex.split(hostname_command), universal_newlines=True)
    hostname = hostname_execute.strip("\n")
    return hostname

def get_fwd_lookup(fwd_dns_zone, hostname, nwhostproj):
    fwdlookup_command = 'gcloud dns record-sets list --zone=' + fwd_dns_zone + ' --project=' + nwhostproj + ' --name="' + hostname + \
        '" --format="value(DATA)"'
    fwdlookup_execute = subprocess.check_output(shlex.split(fwdlookup_command), universal_newlines=True)
    fwdlookup = fwdlookup_execute.strip('\n')
    return fwdlookup

def get_dns_backup(fwd_dns_zone,rev_dns_zone,nwhostproj):
    fwdbackup_command = 'gcloud dns record-sets export ' + fwd_dns_zone + '_backup.txt --project=' + nwhostproj + ' --zone ' + fwd_dns_zone + ' --zone-file-format'
    subprocess.run(shlex.split(fwdbackup_command))
    revbackup_command = 'gcloud dns record-sets export ' + rev_dns_zone + '_backup.txt --project=' + nwhostproj + ' --zone ' + fwd_dns_zone + ' --zone-file-format'
    subprocess.run(shlex.split(revbackup_command))

def get_rev_lookup(rev_dns_zone, hostname, nwhostproj):
    revlookup_command = 'gcloud dns record-sets list --zone=' + rev_dns_zone +  ' --project=' + nwhostproj + ' --filter="DATA ~ ' + hostname + \
        '" --format="value(NAME)"'
    revlookup_execute = subprocess.check_output(shlex.split(revlookup_command), universal_newlines=True)
    revlookup = revlookup_execute.strip('\n')
    return revlookup

def mod_fwd_lookup(nwhostproj,fwd_dns_zone,tgtipaddr,hostname,fwdlookup):
    try:
        txn_start_command = 'gcloud beta dns --project=' + nwhostproj + ' record-sets transaction start --zone='+ fwd_dns_zone
        subprocess.check_output(shlex.split(txn_start_command))
        txn_add_record = 'gcloud beta dns --project=' + nwhostproj + ' record-sets transaction add ' + tgtipaddr + \
            ' --name='+ hostname + '. --ttl=300 --type=A --zone=' + fwd_dns_zone
        subprocess.check_output(shlex.split(txn_add_record))
        txn_rmv_record = 'gcloud beta dns --project=' + nwhostproj + ' record-sets transaction remove ' + fwdlookup + \
            ' --name='+ hostname + '. --ttl=300 --type=A --zone=' + fwd_dns_zone
        subprocess.check_output(shlex.split(txn_rmv_record))
        txn_exec = 'gcloud beta dns --project=' + nwhostproj + ' record-sets transaction execute --zone=' + fwd_dns_zone
        subprocess.check_output(shlex.split(txn_exec))
    except Exception as err:
        print('\u001b[31;1m\nErrors faced while starting a DNS transaction for host - ' + hostname + '\u001b[0m')
        print('\nPlease execute/abort as per URL :\nhttps://cloud.google.com/sdk/gcloud/reference/dns/record-sets/transaction')

def mod_rev_lookup(tgtipaddr,revlookup,nwhostproj,rev_dns_zone,hostname):
    try:
        fourthoctet  = tgtipaddr.rsplit('.',1)[1]
        thirdoctet = tgtipaddr.rsplit('.',2)[1]
        revaddr = fourthoctet + '.' + thirdoctet + '.' + revlookup.split('.',2)[2]
        txn_start_command = 'gcloud beta dns --project=' + nwhostproj + \
            ' record-sets transaction start --zone=' + rev_dns_zone
        subprocess.check_output(shlex.split(txn_start_command))
        txn_add_record = 'gcloud beta dns --project=' + nwhostproj + \
            ' record-sets transaction add ' + hostname + '. --name=' + revaddr + ' --ttl=300 --type=PTR --zone=' + rev_dns_zone
        subprocess.check_output(shlex.split(txn_add_record))
        txn_rmv_record = 'gcloud beta dns --project=' + nwhostproj + \
            ' record-sets transaction remove ' + hostname + '. --name=' + revlookup + ' --ttl=300 --type=PTR --zone=' + rev_dns_zone
        subprocess.check_output(shlex.split(txn_rmv_record))
        txn_exec = 'gcloud beta dns --project=' + nwhostproj + ' record-sets transaction execute --zone=' + rev_dns_zone
        subprocess.check_output(shlex.split(txn_exec))
    except Exception as err:
        print('\u001b[31;1m\nErrors faced while starting a reverse DNS transaction for host - ' + hostname )
        print('\nPlease execute/abort as per URL :\u001b[0m\nhttps://cloud.google.com/sdk/gcloud/reference/dns/record-sets/transaction')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-sp","--sourceprojectid", help="enter target project id(e.g. gcp-<rid>-<region>-dev-proj", type=str)
    parser.add_argument("-np","--nwhostproject", help="enter network host project id(e.g. gcp-<rid>-global-net-proj)", type=str)
    parser.add_argument("-sz","--sourcezone", help="enter source zone of VM(e.g. us-east4-a)", type=str)
    parser.add_argument("-fd","--forwarddnszone", help="enter forward dns zone name", type=str)
    parser.add_argument("-rd","--reversednszone", help="enter reverse dns zone name", type=str)
    parser.add_argument("-csv","--csvfilename", help="enter name of csv file", type=str)
    if len(sys.argv)<13:
        parser.print_help()
        sys.exit(1)
    args = parser.parse_args()
    fwd_dns_zone = args.forwarddnszone
    rev_dns_zone = args.reversednszone
    srczone = args.sourcezone
    csvname = args.csvfilename
    nwhostproj = args.nwhostproject
    srcprojid = args.sourceprojectid
    print('\nBacking up forward and reverse zone entries to <zone-name>_backup.txt file on current path...\n')

    get_dns_backup(fwd_dns_zone=fwd_dns_zone,rev_dns_zone=rev_dns_zone,nwhostproj=nwhostproj)
    
    #Read arguments and user inputs and loop over vms
    with open(csvname, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for line in reader:
            vmname = line["VM Name"],
            vmname = (str(vmname[0]))
            tgtipaddr = str(line["Target IP address"])
            print('\n************************************************************')
            print('Fetching DNS entries for ' + vmname)
            print('************************************************************')
            #get_vm_hostname function to look for hostname from vmname in gcloud.
            try:
                hostname = get_vm_hostname(srczone=srczone,vmname=vmname,srcprojid=srcprojid)
            except:
                print('\u001b[31;1mVM ' + vmname + ' was not found in project ' + srcprojid + ' and zone ' + srczone + \
                       '\nPlease check if VM name in csv and/or parameter values for source project(-sp) and source zone(-sz) are correct!\u001b[0m')
            
            #get_fwd_lookup function to fetch forward entry for hostname - 'A' record.
            try:
                fwdname = get_fwd_lookup(fwd_dns_zone=fwd_dns_zone,hostname=hostname,nwhostproj=nwhostproj)
                revname = get_rev_lookup(rev_dns_zone=rev_dns_zone,hostname=hostname,nwhostproj=nwhostproj)
                print('\u001b[34;1mBefore change :\u001b[0m Forward entry is - \u001b[34;1m' + fwdname + '\u001b[0m | Reverse entry is - \u001b[34;1m' + revname + '\n\u001b[0m')
                mod_fwd_lookup(nwhostproj=nwhostproj,fwd_dns_zone=fwd_dns_zone,tgtipaddr=tgtipaddr,hostname=hostname,fwdlookup=fwdname)
                mod_rev_lookup(tgtipaddr=tgtipaddr,revlookup=revname,nwhostproj=nwhostproj,rev_dns_zone=rev_dns_zone,hostname=hostname)
                fwdname = get_fwd_lookup(fwd_dns_zone=fwd_dns_zone,hostname=hostname,nwhostproj=nwhostproj)
                revname = get_rev_lookup(rev_dns_zone=rev_dns_zone,hostname=hostname,nwhostproj=nwhostproj)
                print('\u001b[34;1m\nAfter Change :\u001b[0m Forward entry is - \u001b[34;1m' + fwdname + '\u001b[0m | Reverse entry is - \u001b[34;1m' + revname + '\u001b[0m')
            except:
                print('\u001b[31;1m\nError fetching DNS lookup entries for corresponding hostname\u001b[0m')
                      
if __name__ == "__main__":
    main()
