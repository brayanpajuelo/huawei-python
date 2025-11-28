from paramiko import SSHClient, AutoAddPolicy
from ncclient import manager
from datetime import date
from time import sleep

devicename = 'X_T1_AGG1'
deviceip = '10.1.0.6'
logserver = '10.1.60.2'
username = 'python'
password = 'Huawei@123'
nc_username = 'netconf'
nc_password = 'Huawei@123'
logname = 'huawei'

YANGxml = f'''
<config>
    <syslog:syslog xmlns:syslog="urn:ietf:params:xml:ns:yang:ietf-syslog">
		<syslog:log-actions>
			<syslog:remote>
				<syslog:destination>
					<syslog:name>{logname}</syslog:name>
					<syslog:udp>
						<syslog:address>{logserver}</syslog:address>
						<syslog:port>43</syslog:port>
					</syslog:udp>
				</syslog:destination>
			</syslog:remote>
		</syslog:log-actions>
	</syslog:syslog>
</config>
'''

class Datacom():
    def __init__(self, deviceip, username, password):
        self.server = deviceip
        self.username = username
        self.password = password
        self.client = self._GetClient()

    def _GetClient(self):
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy)
        client.connect(self.server, username=self.username, password=self.password)
        return client

    def OpenNetconf(self, cmds):
        shell=self.client.invoke_shell()
        for cmd in cmds:
            shell.send(cmd)
            if cmd == 'y\n':
                sleep(15)
            elif 'port 830' in cmd:
                sleep(15)

        x=shell.recv(99999).decode()
        print(x)
        self.client.close()

    def CheckFan(self, faninfo):
        return faninfo.find('Normal') == -1

    def SaveCfg(self, bkpname):
        bkpname += '.zip'
        cmd = f'save force {bkpname}\n'
        shell=self.client.invoke_shell()
        shell.send(cmd)
        sleep(5)

        x=shell.recv(99999).decode()
        print(x)
        self.client.close()

    def DownloadCfg(self, bkpname):
        remotename = bkpname + '.zip'
        localname = bkpname + '.bak'
        self.client.open_sftp().get(remotename, localname)
        print('backup downloaded')
        self.client.close()

    def Monitor(self):
        shell=self.client.invoke_shell()
        with open('command.txt') as f:
            for cmd in f:
                print('executing_' + cmd)
                sleep(1)
                shell.send(cmd)
                sleep(5)
                x=shell.recv(99999).decode()
                print(x)
                if 'fan' in cmd:
                    if self.CheckFan(x):
                        print('all fans are faulty')

        self.client.close()

def NetconfEditCfg(xml, deviceip, username, password):
    with manager.connect_ssh(
        host=deviceip,
        username = username,
        password = password,
        hostkey_verify = False,
        device_params = {"name":"huawei"}
    ) as m:
        x = m.edit_config(config=xml, target="running")
        print(x)


if __name__ == "__main__":
    try:
        #DC = Datacom(deviceip, username, password)        #only the first time
        #with open('opennetconf.txt') as cmds:              #only the first time
        #    DC.OpenNetconf(cmds)                           #only the first time
        NetconfEditCfg(YANGxml, deviceip, nc_username, nc_password)

        today = str(date.today())
        bkpname = today+'_'+devicename

        DC = Datacom(deviceip, username, password)
        DC.SaveCfg(bkpname)
        DC = Datacom(deviceip, username, password)
        DC.DownloadCfg(bkpname)

        while True:
            min = 0
            while min != 1440:  #24 hours
                DC = Datacom(deviceip, username, password)
                DC.Monitor()
                print('waiting 5 minutes')
                sleep(5 * 60)
                min += 5
                print('5 minutes is up, excuting again!')

            today = str(date.today())
            bkpname = today+'_'+devicename

            DC = Datacom(deviceip, username, password)
            DC.SaveCfg(bkpname)
            DC = Datacom(deviceip, username, password)
            DC.DownloadCfg(bkpname)

    except Exception as err:
        print(err)
    except KeyboardInterrupt:
        print('monitoring has stopped!')