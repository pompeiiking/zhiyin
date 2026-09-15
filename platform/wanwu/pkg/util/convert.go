package util

import "strconv"

func I64(s string) (int64, error) {
	return strconv.ParseInt(s, 10, 64)
}

func MustI64(s string) int64 {
	i64, _ := I64(s)
	return i64
}

func I32(s string) (int32, error) {
	i64, err := I64(s)
	if err != nil {
		return 0, err
	}
	return int32(i64), nil
}

func MustI32(s string) int32 {
	i64, _ := I64(s)
	return int32(i64)
}

func U32(s string) (uint32, error) {
	i64, err := I64(s)
	if err != nil {
		return 0, err
	}
	return uint32(i64), nil
}

func MustU32(s string) uint32 {
	i64, _ := I64(s)
	return uint32(i64)
}

func Int2Str[T ~int | ~int32 | ~uint32 | ~int64](i T) string {
	return strconv.FormatInt(int64(i), 10)
}
