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

def get_rev_lookup(rev_dns_zone, hostname, nwhostproj):
    revlookup_command = 'gcloud dns record-sets list --zone=' + rev_dns_zone +  ' --project=' + nwhostproj + ' --filter="DATA ~ ' + hostname + \
        '" --format="value(NAME)"'
    revlookup_execute = subprocess.check_output(shlex.split(revlookup_command), universal_newlines=True)
    revlookup = revlookup_execute.strip('\n')
    return revlookup

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-sp","--sourceprojectid", help="enter target project id(e.g. gcp-<rid>-<region>-dev-proj", type=str)
    parser.add_argument("-np","--nwhostproject", help="enter network host project id(e.g. gcp-<rid>-global-net-proj)", type=str)
    parser.add_argument("-sz","--sourcezone", help="enter source zone(e.g. us-east4-a)", type=str)
    parser.add_argument("-fd","--forwarddnszone", help="enter forward dns zone name", type=str)
    parser.add_argument("-rd","--reversednszone", help="enter reverse dns zone name", type=str)
    parser.add_argument("-csv","--csvfilename", help="enter name of csv file (full path if file is in other location)", type=str)
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

    with open(csvname, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        for line in reader:
            vmname = line["VM Name"],
            vmname = (str(vmname[0]))
            #tgtipaddr = str(line["Target IP address"])

            hostname = get_vm_hostname(srczone=srczone,vmname=vmname,srcprojid=srcprojid)
            fwdname = get_fwd_lookup(fwd_dns_zone=fwd_dns_zone,hostname=hostname,nwhostproj=nwhostproj)
            revname = get_rev_lookup(rev_dns_zone=rev_dns_zone,hostname=hostname,nwhostproj=nwhostproj)
            print('Hostname : \u001b[34;1m' + hostname + '\u001b[0m : Forward entry - \u001b[34;1m' + fwdname + '\u001b[0m | Reverse entry - \u001b[34;1m' + revname + '\n\u001b[0m')

if __name__ == "__main__":
    main()
