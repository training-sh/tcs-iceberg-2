"""Rebuild the flat architecture illustrations (Pillow; SVG + PNG)."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W,H=1440,900
COLORS={'blue':'#2563EB','teal':'#0D9488','purple':'#7C3AED','orange':'#EA580C','pink':'#DB2777','slate':'#475569'}
class Figure:
 def __init__(self,title,sub):
  self.im=Image.new('RGB',(W*2,H*2),'#F8FAFC');self.d=ImageDraw.Draw(self.im)
  self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img"><title>{escape(title)}</title><rect width="1440" height="900" fill="#F8FAFC"/>']
  self.text(52,36,title,34,'#0F172A',True);self.text(52,88,sub,19,'#475569')
 def text(self,x,y,s,size=20,color='#334155',bold=False):
  font=ImageFont.truetype('C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'arial.ttf'),size*2)
  self.d.text((x*2,y*2),s,font=font,fill=color)
  self.svg.append(f'<text x="{x}" y="{y+size}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(s)}</text>')
 def rect(self,x,y,w,h,fill,stroke='#CBD5E1'):
  self.d.rounded_rectangle((x*2,y*2,(x+w)*2,(y+h)*2),radius=22,fill=fill,outline=stroke,width=2)
  self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="11" fill="{fill}" stroke="{stroke}"/>')
 def card(self,x,y,w,h,title,lines,color='blue'):
  c=COLORS[color];self.rect(x,y,w,h,'#FFFFFF');self.rect(x+16,y+20,6,h-40,c,c)
  self.text(x+36,y+22,title,23,c,True)
  for i,line in enumerate(lines):self.text(x+36,y+67+i*31,line,19)
 def arrow(self,x,y,xx,yy,label=''):
  c='#64748B';self.d.line((x*2,y*2,xx*2,yy*2),fill=c,width=4)
  import math
  a=math.atan2(yy-y,xx-x);p=[(xx,yy),(xx-12*math.cos(a-.5),yy-12*math.sin(a-.5)),(xx-12*math.cos(a+.5),yy-12*math.sin(a+.5))]
  self.d.polygon([(a*2,b*2) for a,b in p],fill=c)
  self.svg.append(f'<path d="M{x} {y} L{xx} {yy}" stroke="{c}" stroke-width="2"/><polygon points="'+ ' '.join(f'{a},{b}' for a,b in p)+f'" fill="{c}"/>')
  if label:self.text((x+xx)/2+8,(y+yy)/2-26,label,17,c)
 def save(self,name):
  self.text(52,856,'OPENSHiFT / CRC  •  DATA ENGINEERING LAB  •  Logical architecture',15,'#64748B')
  self.im.save(OUT/(name+'.png'));(OUT/(name+'.svg')).write_text(''.join(self.svg)+'</svg>',encoding='utf-8')

f=Figure('One cluster. A complete data engineering lab.','Ubuntu host → KVM / libvirt → CRC virtual machine → single OKD node')
f.rect(32,137,1376,687,'#EFF6FF','#93C5FD');f.text(55,153,'CRC / OKD  |  control plane + application workloads on one node',23,'#2563EB',True)
f.card(55,210,420,240,'COMPUTE & SQL',['Spark master + worker','JupyterLab + Spark History Server','HiveServer2 + Hive Metastore','Trino query engine'],'blue')
f.card(510,210,420,240,'CATALOG & DATABASES',['Polaris: Iceberg REST catalog','PostgreSQL: Polaris service state','MySQL: Hive metastore + SQL','Catalog metadata ≠ dataset files'],'purple')
f.card(965,210,420,240,'DATA STORAGE & EVENTS',['HDFS: NameNode + DataNode','SeaweedFS: S3 object warehouse','Kafka: event topics','ZooKeeper: Kafka coordination'],'teal')
f.card(55,480,650,140,'HADOOP EXECUTION',['YARN ResourceManager + NodeManager','MapReduce HistoryServer'],'orange')
f.card(735,480,650,140,'OBSERVABILITY & WORKFLOWS',['Prometheus • Grafana • Loki • Alloy • Jaeger','Airflow • Marquez  |  additional lesson services'],'pink')
f.card(55,650,1330,148,'OPENSHIFT FOUNDATION',['API server • etcd • scheduler • controllers • Operators','DNS • network • ingress/router • OAuth • console • image registry • persistent storage'],'slate');f.save('03-cluster-overview')

f=Figure('Look inside a pod','A pod groups containers that share networking and mounted volumes.')
f.rect(45,155,1350,650,'#EFF6FF','#93C5FD');f.text(70,177,'Namespace: bigdata',24,'#2563EB',True)
f.card(75,235,610,265,'POD  spark-master-0',['CONTAINER  spark-master  → scheduling','CONTAINER  spark-history  → completed jobs','CONTAINER  jupyter  → notebook + driver','Shared pod IP • localhost between containers','PVC mounts hold notebooks / event logs'],'blue')
f.card(725,235,590,265,'POD  spark-worker-0',['CONTAINER  spark-worker','Worker launches executor JVM processes','Executors run tasks for Spark applications','Executors are processes in this layout,','not separate Kubernetes executor pods.'],'teal')
f.arrow(685,350,725,350)
f.card(75,545,1240,200,'ONE IMAGE CAN CREATE MANY CONTAINERS',['The Spark image supplies software; each container starts a different command.','Service spark-master provides a stable name while pod IPs may change.','A pod restart replaces running containers; PVCs retain the mounted persistent data.'],'purple');f.save('03-pods-containers')

f=Figure('Two warehouses. Separate metadata and data.','Follow catalog calls separately from the files read and written by query engines.')
f.card(455,150,530,145,'CLIENT / QUERY ENGINE',['Spark + Iceberg client  /  Trino'],'blue')
f.card(75,380,570,155,'POLARIS  :8181',['REST catalog → table registration / locations','Backend: PostgreSQL database polaris'],'purple')
f.card(800,380,570,155,'SEAWEEDFS S3  :8333',['s3://warehouse/iceberg','Iceberg metadata JSON, manifests + data files'],'teal')
f.arrow(540,295,360,380,'catalog calls');f.arrow(900,295,1080,380,'file I/O')
f.card(75,635,570,155,'HIVE METASTORE  :9083',['Table / column / partition definitions','Backend: MySQL database hive_metastore'],'purple')
f.card(800,635,570,155,'HDFS  :9000',['NameNode: namespace + block locations','DataNode: actual file blocks on disk'],'teal')
f.text(75,572,'HiveServer2 / configured Hive clients use the Hive metadata and HDFS paths.',21,'#475569')
f.arrow(645,710,800,710,'locations');f.save('03-data-metadata')

f=Figure('Hadoop and Hive: who does what?','Kubernetes runs the services. YARN manages Hadoop application execution inside the lab.')
f.card(60,165,400,180,'HIVE SQL',['HiveServer2 accepts SQL / JDBC','Metastore describes tables','MySQL persists metastore rows'],'purple')
f.card(520,165,400,180,'YARN SCHEDULING',['ResourceManager allocates work','NodeManager launches processes','HistoryServer shows finished jobs'],'orange')
f.card(980,165,400,180,'HDFS STORAGE',['NameNode tracks block locations','DataNode stores the file blocks','Separate persistent volume claims'],'teal')
f.arrow(460,255,520,255);f.arrow(920,255,980,255)
f.card(60,405,630,170,'PODS / CONTAINERS',['resourcemanager-*  [resourcemanager]','nodemanager-*  [nodemanager]','historyserver-*  [historyserver]'],'orange')
f.card(730,405,650,170,'PODS / CONTAINERS',['hive-metastore-*  [hive-metastore]','hiveserver2-*  [hiveserver2]','namenode-0 [namenode] • datanode-0 [datanode]'],'teal')
f.card(60,635,1320,160,'TWO DIFFERENT MEANINGS OF “CONTAINER”',['Kubernetes container: an image-based runtime unit inside a pod.','YARN container: an allocation of memory / CPU for an application process.','This Spark setup uses standalone master / worker scheduling, independently of YARN.'],'blue');f.save('03-hadoop-hive')

f=Figure('CRC also runs the OpenShift platform','System pods live mainly in openshift-* namespaces, alongside the bigdata project.')
items=[('CONTROL PLANE',['kube-apiserver • etcd','kube-scheduler • controller-manager','Cluster state and reconciliation'],'blue'),('NETWORK & DISCOVERY',['dns-default-* • network agents','Service DNS and pod connectivity','OVN components depend on bundle'],'teal'),('BROWSER & LOGIN',['router-default-* • console-*','oauth-openshift-*','Routes, cluster console and identity'],'purple'),('IMAGES & STORAGE',['image-registry-* • storage provisioner','Internal images and PVC provisioning','Local storage lives in the CRC VM'],'orange'),('OPERATORS',['cluster-version-operator-*','DNS / ingress / authentication operators','Manage platform desired state'],'pink'),('NODE SERVICES',['kubelet + CRI-O: host services','Run and supervise pod containers','They are not ordinary application pods'],'slate')]
for i,(t,l,c) in enumerate(items): f.card(55+(i%3)*455,160+(i//3)*280,420,240,t,l,c)
f.text(60,758,'Pod names include generated suffixes; inspect the cluster for its exact names and containers.',21)
f.text(60,796,'CRC disables cluster monitoring by default; application monitoring is a separate stack.',21)
f.save('03-crc-platform')

f=Figure('See what the applications are doing','Metrics, logs, traces and lineage describe different aspects of the same work.')
f.card(65,170,400,170,'APPLICATION PODS',['Spark • Hadoop • Hive • Kafka','SQL engines • databases','Instrumented jobs / clients'],'blue')
f.card(535,170,395,170,'COLLECT / STORE',['Prometheus  → metrics','Alloy → Loki  → logs','Jaeger  → emitted traces'],'teal')
f.card(1000,170,375,170,'EXPLORE',['Grafana dashboards','Jaeger trace UI','Marquez lineage UI'],'purple')
f.arrow(465,255,535,255);f.arrow(930,255,1000,255)
f.card(65,430,630,245,'WORKFLOW & LINEAGE',['Airflow runs DAG tasks and schedules workflows.','PostgreSQL stores Airflow metadata.','OpenLineage-enabled jobs emit lineage events.','Marquez stores lineage in PostgreSQL;','marquez-web presents it in a browser.'],'orange')
f.card(735,430,640,245,'POD AND CONTAINER DETAILS',['Some lesson manifests include file-logs sidecars.','Sidecars forward selected log files to stdout.','Alloy can collect the resulting container logs.','Installing tracing / lineage services alone','does not instrument every application.'],'pink')
f.text(65,755,'These services are defined in the lesson manifests; use the inventory slide to see running workloads.',20)
f.save('03-observability')
