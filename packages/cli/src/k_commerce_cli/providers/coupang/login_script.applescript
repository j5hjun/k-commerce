on humanDelay(minMs, maxMs)
	delay ((random number from minMs to maxMs) / 1000)
end humanDelay

set coupangId to "쿠팡아이디"
set coupangPw to "쿠팡비밀번호"

tell application "Google Chrome"
	activate
	open location "https://login.coupang.com/login/login.pang"
end tell

my humanDelay(1000, 3000)

tell application "System Events"
	
	repeat 5 times
		key code 48
		my humanDelay(100, 300)
	end repeat
	
	-- 아이디 한방 입력
	keystroke coupangId
	
	my humanDelay(500, 1200)
	
	key code 48
	
	my humanDelay(300, 700)
	
	-- 비밀번호 한방 입력
	keystroke coupangPw
	
	my humanDelay(800, 1500)
	
	repeat 3 times
		key code 48
		my humanDelay(100, 300)
	end repeat
	
	my humanDelay(500, 1000)
	
	key code 36
	
end tell