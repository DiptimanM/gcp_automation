# gcp_automation
Python scripts for GCP automation

README file for all scripts:

Common points to be kept in mind:

1> Please execute the script after ensuring that the console cloud shell is associated to the correct source project.
	
2> In case of failover, source project/region/zone is the primary site.

3> In case of failback, source project/region/zone is the DR site.

4> The first row of the csv file should not be modified, because the script reads inputs based on the headers.

5> During failback, ensure that the VM names are changed to reflect their DR names and the target IP addresses are adjusted.
	- Same csv file will not work for failover and failback.
	
6> In case of multiple snapshots for the given date, the latest one is considered by default.
	
Separate readme files have been created for each script with usage and sample command.
	
