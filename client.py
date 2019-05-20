import argparse, re, json, time, requests

class Client:
    def __init__(self,host,port):
        self.host = host
        self.port = port
    
    @property
    def url(self):
        url = ""
        url = self.host+":"+str(self.port)
        p = r'^(?:https?|\w+:\/\/)?([-\w.]+)(?::?(\d+)?([\/\w]+)?|\/.*)$'
        m = re.match(p, url, re.I)
        return "http://{}:{}".format(m.group(1),m.group(2))

    def resolve_nodes(self,nodes=None):
        print("="*50)
        print("Starting nodes resolution")
        if nodes is None:
            print("Requesting nodes...")
            nodes = self.get_nodes()
        if nodes:
            # If we recived the node list
            for node in nodes:
                print("Resolving:",node)
                # Iterate over each node
                data = {'node': node}
                r = requests.post(self.url+"/nodes/resolve",data=json.dumps(data))
                if r.status_code==201:
                    print("Executed resolution for:",node)
                else:
                    print("Resolution request for {} failed".format(node))
        else:
            print("Error requesting nodes")
        print("Ended nodes resolution")
        print("="*50)
    def get_nodes(self):
        try:
            r = requests.get(self.url+"/nodes")
            if r.status_code==200:
                nodes = json.loads(r.text)
                return [str(n) for n in nodes]
            else:
                raise Exception("Couldn't pull nodes from "+self.url)
        except Exception as e:
            print("Error:",str(e))
            return False
    
    def resolve_transactions(self, nodes):
        print("="*50)
        print("Resolving transactions")
        for node in nodes:
            print("Resolving transactiond with node:",node)
            try:
                url = self.url+"/transactions/resolve"
                print("URL:",url)
                data = {'node':node}
                r = requests.post(url,data=json.dumps(data))
                if r.status_code==201:
                    print("Transaction resolve started")
                else:
                    print("Error requesting transaction resolve:",r.status_code)
                    print("Content:",r.content)
            except Exception as e:
                print("Error resolving transactions with node:",node)
        print("Ended resolving transactions")
        print("="*50)

    def clean_transactions(self):
        print("Cleaning transactions...")
        try:
            r = requests.get(self.url+"/transactions/clean")
            if r.status_code==201:
                print("Done!")
            else:
                print("Error")
        except Exception as e:
            print("Error cleaning transactions:",str(e))
    
    def resolve_transactions_all(self):
        print("Resolving transactions")
        try:
            url = self.url+"/transactions/resolve"
            r = requests.get(url)
            if r.status_code==201:
                print("Resolve started!")
            else:
                print("Request error!")
        except Exception as e:
            print("Error:",str(e))
    def resolve_nodes_all(self):
        print("Resolving nodes")
        try:
            url = self.url+"/nodes/resolve"
            r = requests.get(url)
            if r.status_code==201:
                print("Resolve started")
            else:
                print("Request error")
        except Exception as e:
            print("Error:",str(e))
    def is_working(self):
        try:
            r = requests.get(self.url+"/working")
            j = r.json()
            if r.status_code==200:
                return not (j['chains'] or j['transactions'])
            else:
                raise Exception("Error, status code:",r.status_code)
        except Exception as e:
            print("Error:",str(e))
def main(args):
    client = Client(args.host, args.port)
    n = 0
    print("Client started!")
    while True:
        print("Starting iteration:",n)
        client.clean_transactions()
        client.resolve_nodes_all()
        client.resolve_transactions_all()
        print("Ended iteration:",n)
        time.sleep(5)
        while True:
            if client.is_working():
                time.sleep(1)
            else:
                break
            

        


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-H","--host",default="http://localhost",type=str,help="Host where the node runs on.")
    parser.add_argument("-p","--port",default=5000,type=int, help="Port where node listens")
    args = parser.parse_args()

    main(args)