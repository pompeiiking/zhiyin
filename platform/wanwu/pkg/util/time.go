package util

import "time"

var UTC8 *time.Location

const timeMsFormat = "2006-01-02 15:04:05.000"

const timeFormat = "2006-01-02 15:04:05"
const dateFormat = "2006-01-02"

func InitTimeLocal() error {
	loc, err := time.LoadLocation("Asia/Shanghai")
	if err != nil {
		return err
	}
	UTC8 = loc
	return nil
}

// WeekStartTime 某周的开始时间(周一0点)，-1上周，0本周，1下周
func WeekStartTime(t time.Time, week int) time.Time {
	offset := time.Monday - t.Weekday()
	if offset > 0 { // 周日特殊处理
		offset = -6
	}
	y, m, d := t.Date()
	today := time.Date(y, m, d, 0, 0, 0, 0, t.Location())
	return today.AddDate(0, 0, int(offset)+week*7)
}

func Time2Str(millSec int64) string {
	return time.UnixMilli(millSec).In(UTC8).Format(timeFormat)
}

func Time2MsStr(millSec int64) string {
	return time.UnixMilli(millSec).In(UTC8).Format(timeMsFormat)
}

func Str2Time(timeStr string) (int64, error) {
	t, err := time.ParseInLocation(timeFormat, timeStr, UTC8)
	if err != nil {
		return 0, err
	}
	return t.UnixMilli(), nil
}

func Str2Date(timeStr string) (int64, error) {
	t, err := time.ParseInLocation(dateFormat, timeStr, UTC8)
	if err != nil {
		return 0, err
	}
	return t.UnixMilli(), nil
}
