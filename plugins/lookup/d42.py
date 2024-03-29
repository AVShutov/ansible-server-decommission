from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
import json, requests, imp, sys, csv, io, os

if 'D42_SKIP_SSL_CHECK' in os.environ and os.environ['D42_SKIP_SSL_CHECK'] == 'True':
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

if 'D42_USERNAME' not in os.environ:
    print ('Please set D42_USERNAME environ.')
    sys.exit()

if 'D42_PASSWORD' not in os.environ:
    print ('Please set D42_PASSWORD environ.')
    sys.exit()

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class LookupModule(LookupBase):

    @staticmethod
    def get_list_from_csv(text):
        f = io.StringIO(text.decode("utf-8"))
        output_list = []
        dict_reader = csv.DictReader(f, quotechar='"', delimiter=',', quoting=csv.QUOTE_ALL, skipinitialspace=True, dialect='excel')
        for item in dict_reader:
            output_list.append(item)

        if len(output_list) == 1:
            output_list = [output_list,]

        return output_list

    def run(self, terms, variables=None, **kwargs):
        conf = {
            'D42_URL': os.getenv('D42_URL', 'https://device42.example.com/'),
            'D42_USER': os.environ['D42_USERNAME'],
            'D42_PWD': os.environ['D42_PASSWORD']
        }
        if terms[1] == "password":
            return self.getUserPass(conf, terms[0], terms[2])
        elif terms[0] == "servicePassword":
            return self.getServicePass(conf, terms[1], terms[2], terms[3])
        elif terms[1] == "doql":
            return self.runDoql(conf, terms[0],  terms[2])
        elif terms[1] == "d42info":
            return self.deviceInfo(conf, terms[0], terms[2])

    def getUserPass(self, conf, device, username):
        url = conf['D42_URL'] + "/api/1.0/passwords/?plain_text=yes&device=" + device + "&username=" + username
        resp = requests.request("GET",
                                url,
                                auth=(conf['D42_USER'], conf['D42_PWD']),
                                verify=False)

        if resp.status_code != 200:
            raise AnsibleError("API Call failed with status code: " + str(resp.status_code))
        if not resp.text:
            raise AnsibleError("Something went wrong!")

        req = json.loads(resp.text)
        req = req["Passwords"]
        if req:
            if len(req) > 1:
                raise AnsibleError("Multiple users found for device: %s" % device)
            return [req[0]["password"]]
        else:
            raise AnsibleError("No password found for user: %s and device: %s" % (username, device))

    def getServicePass(self, conf, username, label, category):
        url = conf['D42_URL'] + "/api/1.0/passwords/?plain_text=yes&username=" + username + "&label=" + label + "&category=" + category

        resp = requests.request("GET",
                                url,
                                auth=(conf['D42_USER'], conf['D42_PWD']),
                                verify=False)

        if resp.status_code != 200:
            raise AnsibleError("API Call failed with status code: " + str(resp.status_code))
        if not resp.text:
            raise AnsibleError("Something went wrong!")

        req = json.loads(resp.text)
        req = req["Passwords"]
        if req:
            if len(req) > 1:
                raise AnsibleError("Multiple users found for device: %s" % device)
            return [req[0]["password"]]
        else:
            raise AnsibleError("No password found for user: %s and device: %s" % (username, device))

    def runDoql(self, conf, query, output_type):
        url = conf['D42_URL'] + "/services/data/v1.0/query/"

        post_data = {
            "query": query.replace("@", "'"),
            "header": 'yes' if output_type == 'list_dicts' else 'no'
        }

        resp = requests.request("POST",
                                url,
                                auth=(conf['D42_USER'], conf['D42_PWD']),
                                data=post_data,
                                verify=False)

        if resp.status_code != 200:
            raise AnsibleError("API Call failed with status code: " + str(resp.status_code))

        if output_type == 'string':
            return [resp.text.replace('\n', ''),]
        elif output_type == 'list':
            return resp.text.split('\n')

        return self.get_list_from_csv(resp.text)

    def deviceInfo(self, conf, device, scrapedMeta):
        url = conf['D42_URL'] + "/api/1.0/devices/?name=" + device
        device_name_blob = requests.request("GET",
                                                  url,
                                                  auth=(conf['D42_USER'], conf['D42_PWD'])
                                                  ).json()
        device_id = device_name_blob['Devices'][0]['device_id']
        device_url = conf['D42_URL'] + "/api/1.0/devices/id/" + str(device_id)
        device_info_blob = requests.request("GET",
                                            device_url,
                                            auth=(conf['D42_USER'], conf['D42_PWD'])
                                            ).json()
        requested_info = device_info_blob[scrapedMeta]
        return [requested_info]
