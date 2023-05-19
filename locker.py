import RPi.GPIO as GPIO
import spidev
import time
import datetime

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# 기록저장초기화
f = open("/home/pi/webapps/soloproject/history.txt", "w")
f.write("")
f.close()

# adc세팅
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 100000

delay = 0.1

sw_channel = 0
vrx_channel = 1
vry_channel = 2

# servo세팅
servo_pin = 18
GPIO.setup(servo_pin, GPIO.OUT)
p = GPIO.PWM(18, 50)
p.start(0)

# led세팅
led_list = [17, 27, 22]
GPIO.setup(led_list, GPIO.OUT)
GPIO.output(led_list, False)

GPIO.output(led_list[0], True)  # 빨간불

# 기타데이터 초기화
password_in = False  # 패스워드 입력중 상태 확인 변수
joycenter = True  # 조이스틱 중립 체크 변수
password_list = [0, 0, 0, 0]  # 입력할 비밀번호
password_num = 0  # password_list index 정수

password_saved = [6, 5, 2, 3]  # 저장된 비밀번호
password_correct = False  # 비밀번호 확인 함수

password_change = [0, 0, 0, 0]  # 변경할 비밀번호
password_change_error = 3  # 에러체크활성화0 에러1 에러없음2 에러체크비활성화3


def readadc(adcnum):  # spi통신
    if adcnum > 7 or adcnum < 0:
        return -1
    r = spi.xfer2([1, (8 + adcnum) << 4, 0])
    data = ((r[1] & 3) << 8) + r[2]
    return data


def direction(vrx, vry):  # 조이스틱 상태에 따라 정수 반환 함수
    num = 0
    if vrx <= 450:
        if vry <= 450:
            num = 1
        elif vrx <= 50 and vry < 550:
            num = 2
        elif vry >= 550:
            num = 3
    elif vrx > 450 and vrx < 550:
        if vry <= 50:
            num = 8
        elif vry >= 973:
            num = 4
    elif vrx >= 550:
        if vry <= 450:
            num = 7
        elif vrx > 973 and vry < 550:
            num = 6
        elif vry >= 550:
            num = 5
    return num


def values():  # adc값 묶어놓은 정리용 함수
    global sw_value, vrx_pos, vry_pos, num
    sw_value = readadc(sw_channel)
    vrx_pos = readadc(vrx_channel)
    vry_pos = readadc(vry_channel)
    num = direction(vrx_pos, vry_pos)


def led_control(r, y, g):  # led제어 함수
    if r == 1:
        GPIO.output(led_list[0], True)
    else:
        GPIO.output(led_list[0], False)
    if y == 1:
        GPIO.output(led_list[1], True)
    else:
        GPIO.output(led_list[1], False)
    if g == 1:
        GPIO.output(led_list[2], True)
    else:
        GPIO.output(led_list[2], False)


def holding():
    global mode
    count = 0
    if password_correct == True:
        while count < 2:
            values()
            time.sleep(0.1)
            if sw_value > 100:
                print("not hold")
                mode = 2
                return mode
            count += 0.1
        print("hold")
        mode = 1
    else:
        print("not hold")
        mode = 2
    return mode


try:  # ctrl+c로 led다 끌려고 만듬
    while True:
        values()
        if password_in == False and sw_value <= 100:  # 패스워드 입력 시작
            holding()  # 2초간 버튼 누르고있는지 바로때는지 확인
            if mode == 1:  # 비번 변경모드
                mode = 0
                ledcounter = 0
                while True:
                    values()
                    if num != 0:
                        while num != 0:
                            if password_num >= len(password_change):  # 입력량이 입력칸보다 많을때
                                for i in range(1, len(password_change)):
                                    password_change[i - 1] = password_change[i]
                                password_num = len(password_change) - 1

                            print("----------------------------")  # 입력상태확인용 출력문
                            print(
                                "x : %d, y : %d, sw : %d, num : %d"
                                % (vrx_pos, vry_pos, sw_value, num)
                            )

                            if num != 0:
                                password_change[password_num] = num

                            values()

                        if password_num < len(password_change):  # index 번호가 길이보다 짧을때
                            password_num += 1

                    print(password_change)

                    if sw_value > 100:  # 비번변경모드 바로 종료되는 현상 방지
                        password_change_error = 0

                    if sw_value <= 100 and password_change_error == 0:  # 변경비번 설정완료시
                        password_num = 0
                        for i in password_change:  # 비밀번호 다 채움 확인
                            if i == 0:
                                password_change_error = 1  # 비번덜입력
                                break
                            else:
                                password_change_error = 2  # 비번다입력

                        if password_change_error == 1:  # 변경에러 입력값초기화
                            for i in range(0, len(password_change)):
                                password_change[i] = 0
                        elif password_change_error == 2:  # 변경성공 입력값 반영 및 초기화
                            for i in range(0, len(password_change)):
                                password_saved[i] = password_change[i]

                            for i in range(0, len(password_change)):
                                password_change[i] = 0

                    if password_change_error == 1:  # 비번변경오류 빨간불 깜빡깜빡
                        f = open("/home/pi/webapps/soloproject/history.txt", "a")
                        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write("[" + t + "]" + " 비밀번호 변경 실패\n")
                        f.close()
                        led_control(1, 0, 0)
                        time.sleep(0.5)
                        led_control(0, 0, 0)
                        time.sleep(0.5)
                        led_control(1, 0, 0)
                        time.sleep(0.5)
                        led_control(0, 0, 0)
                        time.sleep(0.5)
                        led_control(1, 0, 0)
                        time.sleep(0.5)
                        led_control(0, 0, 0)
                        time.sleep(0.5)
                        password_change_error = 4
                        password_correct = False
                        break
                    elif password_change_error == 2:  # 비번변경성공 초록북 깜빡깜빡
                        f = open("/home/pi/webapps/soloproject/history.txt", "a")
                        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write("[" + t + "]" + " 비밀번호 변경 성공 : ")
                        for i in range(0, len(password_saved)):
                            f.write(str(password_saved[i]))
                        f.write("\n")
                        f.close()
                        led_control(0, 0, 1)
                        time.sleep(0.5)
                        led_control(0, 0, 0)
                        time.sleep(0.5)
                        led_control(0, 0, 1)
                        time.sleep(0.5)
                        led_control(0, 0, 0)
                        time.sleep(0.5)
                        led_control(0, 0, 1)
                        time.sleep(0.5)
                        led_control(0, 0, 0)
                        time.sleep(0.5)
                        password_change_error = 4
                        password_correct = False
                        f = open("/home/pi/webapps/soloproject/history.txt", "a")
                        t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.write("[" + t + "]" + " 닫힘\n")
                        f.close()
                        break
                    else:  # 비번변경중 노란불 깜빡깜빡
                        time.sleep(0.1)
                        ledcounter += 1
                        if ledcounter == 5:
                            led_control(0, 1, 0)
                        elif ledcounter >= 10:
                            led_control(0, 0, 0)
                            ledcounter = 0

            elif mode == 2:  # 비번입력모드
                mode = 0
                if password_correct == True:  # 열린상태
                    password_correct = False
                    led_control(1, 0, 0)  # 빨간불
                    f = open("/home/pi/webapps/soloproject/history.txt", "a")
                    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write("[" + t + "]" + " 닫힘\n")
                    f.close()
                else:
                    while password_correct == False:  # 잠긴상태
                        led_control(0, 1, 0)  # 노란불
                        values()

                        if num != 0:
                            while num != 0:
                                if password_num >= len(password_list):  # 입력량이 입력칸보다 많을때
                                    for i in range(1, len(password_list)):
                                        password_list[i - 1] = password_list[i]
                                    password_num = len(password_list) - 1

                                print("----------------------------")  # 입력상태확인용 출력문
                                print(
                                    "x : %d, y : %d, sw : %d, num : %d"
                                    % (vrx_pos, vry_pos, sw_value, num)
                                )

                                if num != 0:
                                    password_list[password_num] = num

                                values()

                            if password_num < len(password_list):  # index 번호가 길이보다 짧을때
                                password_num += 1

                        print(password_list)  # 입력된 비밀번호 확인용 출력문

                        if sw_value > 100:  # 비밀번호 입력 바로 닫히는 현상 방지
                            password_in = True

                        if sw_value <= 100 and password_in == True:  # 비밀번호 제출
                            if password_list == password_saved:  # 비밀번호 확인
                                password_correct = True
                                f = open(
                                    "/home/pi/webapps/soloproject/history.txt", "a"
                                )
                                t = datetime.datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                                f.write("[" + t + "]" + " 열림\n")
                                f.close()
                            else:
                                password_correct = False
                            password_in = False
                            password_num = 0

                            for i in range(0, len(password_list)):  # 입력상태 초기화
                                password_list[i] = 0

                            while True:
                                values()
                                if sw_value > 100:
                                    break

                            break  # 비밀번호 입력모드 종료

        if password_correct == True:
            led_control(0, 0, 1)  # 초록불
            p.ChangeDutyCycle(7.5)
        else:
            led_control(1, 0, 0)  # 빨간불
            p.ChangeDutyCycle(2.5)

        print("----------------------------")  # 입력상태확인용 출력문
        print("x : %d, y : %d, sw : %d, num : %d" % (vrx_pos, vry_pos, sw_value, num))
        time.sleep(delay)

except KeyboardInterrupt:  # 콘솔 ctrl+c 클린정지
    print("measurement stoped by user")
    GPIO.cleanup()
