import requests
from bs4 import BeautifulSoup
import re

import time
from icalendar import Calendar, Event, vText
import datetime
import pytz

import codecs
import base64
from jsbn import RSAKey

class JWXT:
    """
    Login to the NEUQ educational system, 
    crawling the class schedule and convert to ics format.
    """
    baseUrl = 'http://jwxt.neuq.edu.cn'
    sessions = requests.Session()
    time = str(int(time.time()))
    headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'}



    def __init__(self,username,password):
        self.username = username
        self.password = password
        self.getCsrfToken()
        self.getRSApublickey()
        self.login()
        self.getYearTerm()
        self.getNormalClassTable()
        self.getSysClassTable()
        self.cal = self.lessonToCal().to_ical()
        self.generateIcs()  

    def getCsrfToken(self):
        """
        Get the csrftoken through the BeautifulSoup library.
        """
        url = self.baseUrl + '/jwglxt/xtgl/login_slogin.html?language=zh_CN&_t=' +self.time
        try:
            response = self.sessions.get(url,headers=self.headers)
        except:
            print('请检查网络连接..')
            exit()
        soup = BeautifulSoup(response.text, 'html.parser')
        self.csrftoken = soup.find(id="csrftoken")['value']

    def getRSApublickey(self):
        """
        Get the RSA encryption public key.
        """
        url = self.baseUrl + '/jwglxt/xtgl/login_getPublicKey.html?time=' + self.time
        response = self.sessions.get(url,headers=self.headers)
        self.publicKey = response.json()

    
    def encryptPassword(self):
        """
        Encrypt password By RSA.
        """
        # base64 to hex
        self.exponent = codecs.encode(base64.b64decode(self.publicKey["exponent"]),encoding="hex").decode("utf-8")
        self.modulus = codecs.encode(base64.b64decode(self.publicKey["modulus"]),encoding="hex").decode("utf-8")

        rsa = RSAKey()
        rsa.setPublic(self.modulus, self.exponent)
        cry_data = rsa.encrypt(self.password)
        
        # hex to base64
        return base64.b64encode(codecs.decode(cry_data,encoding="hex")).decode("utf-8")

    def login(self):
        """
        Login and get cookie.
        """
        url = self.baseUrl + '/jwglxt/xtgl/login_slogin.html'
        mm = self.encryptPassword()
        data = {
            'csrftoken':self.csrftoken,
            'yhm':self.username,
            'mm':mm, 
            'mm':mm
        }
        response = self.sessions.post(url,headers = self.headers,data=data)
        self.cookie = response.request.headers['cookie']

        if re.findall(r'用户名或密码不正确', response.text):
            print('用户名或密码错误,请查验..')
            exit()
                
    def getYearTerm(self):
        """
        Input current year and term.
        """
        self.year = input("请输入年份(如2018-2019,输入2018)):").strip()
        term = input("请输入学期(1或2):")
        self.term = '3' if term == '1' else '12'
        self.fullTerm = '('+self.year+'-'+str(int(self.year)+1)+'-'+term+')'+'课表'
        firstWeek = input("请输入第一周日期(如20180903):")
        self.firstWeek = datetime.date(int(firstWeek[:4]),int(firstWeek[4:6]),int(firstWeek[-2:]))

    def getNormalClassTable(self):
        """
        Get daily schedules.
        """
        sysUrl = self.baseUrl + '/jwglxt/kbcx/xskbcx_cxXsKb.html?gnmkdm=N253508'
        data = {
            'xnm': self.year,
            'xqm': self.term,
        }
        response = self.sessions.post(sysUrl,headers = self.headers, data = data)
        self.lessons = response.json()
    
    def getSysClassTable(self):
        """
        Get the experiment schedule.
        """
        sysUrl = self.baseUrl + '/jwglxt/xssygl/sykbcx_cxSykbcxxsIndex.html?doType=query&gnmkdm=N253508'
        data = {
            'xnm': self.year,
            'xqm': self.term,
            '_search': 'false',
            'nd': self.time,
            'queryModel.showCount': 15,
            'queryModel.currentPage': 1,
            'queryModel.sortName':'',
            'queryModel.sortOrder': 'asc',
            'time': 1,
        }
        response = self.sessions.post(sysUrl,headers = self.headers, data = data)
        self.syLessons = response.json()

    def lessonToCal(self):
        """
        Convert the class schedule to ical.
        """
        c = Calendar()
        # First day of school
        firstWeek = self.firstWeek
        c.add('prodid', '-//My calendar product//mxm.dk//')
        c.add('version', '2.0')

        for i in self.lessons['kbList']:
            weeks = getClassWeek(i['zcd'])

            for j in weeks:
                time = getClassTime(firstWeek+datetime.timedelta(days=(int(i['xqj'])-1+(j-1)*7)),i['jcs'])
                
                e = Event()
                e.add('summary', i['kcmc'])
                e.add('location', i['cdmc'])
                e.add('dtstart', time[0])
                e.add('dtend', time[1])
                e.add('description',"周数: "+i['zcd']+"\n"+"节数: "+i['xqjmc']+" "+i["jc"]+"\n"+"老师: "+i['xm']+"\n"+"地点: "+i['cdmc'])
                
                c.add_component(e)

        for k in self.syLessons['items']:
            weeks = getClassWeek(k['zcd'])
            for kk in weeks:
                time = getClassTime(firstWeek+datetime.timedelta(days=(int(k['xqj'])-1+(kk-1)*7)),k['jcs'])
                
                e = Event()
                e.add('summary', k['kcmc']+' '+k['xmmc'])
                e.add('location', k['syfj'])
                e.add('dtstart', time[0])
                e.add('dtend', time[1])
                e.add('description',"周数: "+k['zcd']+"\n"+"节数: "+k['xqjmc']+" "+k["jc"]+"\n"+"老师: "+k['jsxm']+"\n"+"地点: "+k['syfj'])
                
                c.add_component(e)

        return c
    def generateIcs(self):
        with open(self.lessons['xsxx']['XM']+self.fullTerm+".ics", 'wb') as my_file:
            my_file.write(self.cal)

def getClassTime(ymd,b2e):
    """
    Get class start time and end time.
    """
    time_table = {
        "1":[8,0],
        "2":[9,0],
        "3":[10,15],
        "4":[11,15],
        "5":[14,0],
        "6":[15,0],
        "7":[16,15],
        "8":[17,15],
        "9":[19,0],
        "10":[20,0]
    }
    res = b2e.split('-')
    time = []
    t1 = datetime.time(int(time_table[res[0]][0]),int(time_table[res[0]][1]),tzinfo=pytz.timezone('Asia/Shanghai'))
    t2 = datetime.time(int(time_table[res[1]][0]),int(time_table[res[1]][1]),tzinfo=pytz.timezone('Asia/Shanghai'))
    time.append(datetime.datetime.combine(ymd,t1))
    time.append(datetime.datetime.combine(ymd,t2)+ datetime.timedelta(minutes=50))
    return time

def getClassWeek(zcd):
    """
    Get class week. 
    """
    interval = zcd.split(",")
    weeks = []
    for week in interval:
        leap = 1
        if ("(双)" or "(单)") in week:
            week = week.replace("(双)","")
            week = week.replace("(单)","")
            leap = 2
        real = week[:-1].split('-')
        if len(real) == 1:
            weeks += [int(real[0])]
        else:
            weeks += [i for i in range(int(real[0]),int(real[1]) + 1, leap)]
    return weeks