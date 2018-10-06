import getpass
from jwxt import JWXT

def main():
    username = input('请输入学号:').strip()
    password = getpass.getpass('请输入密码(密码不回显,输入完回车即可):').strip()
    J = JWXT(username, password)
    J.getCsrfToken()
    J.getRSApublickey()
    J.login()
    J.getYearTerm()
    J.getNormalClassTable()
    J.getSysClassTable()
    res = J.lessonToCal().to_ical()
    
    with open(J.lessons['xsxx']['XM']+J.fullTerm+".ics", 'wb') as my_file:
        my_file.write(res)

if __name__ == '__main__':
    main()