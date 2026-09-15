package log

import (
	"errors"
	"os"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
)

// Config 日志文件配置
type Config struct {
	Enable     bool    `json:"enable" mapstructure:"enable"`
	Filename   string  `json:"filename" mapstructure:"filename"` // 日志文件名
	Level      string  `json:"level" mapstructure:"level"`       // 日志等级
	LevelOp    LevelOp `json:"level_op" mapstructure:"level_op"`
	MaxSize    int     `json:"max_size" mapstructure:"max_size"`       // 日志切割大小，m为单位
	MaxBackups int     `json:"max_backups" mapstructure:"max_backups"` // 日志最大保留个数
	MaxAge     int     `json:"max_age" mapstructure:"max_age"`         // 日志最大保留天数
}

type LevelOp int32

const (
	LevelLT LevelOp = -2 // less than
	LevelLE LevelOp = -1 // less equal
	LevelGE LevelOp = 0  // great equal
	LevelEQ LevelOp = 1  // equal
	LevelGT LevelOp = 2  // great than
)

// 打印等级 Panic > Error > Warn > Info > Debug

var slog *zap.SugaredLogger

func init() {
	encoder := getEncoder()
	core := zapcore.NewCore(encoder, os.Stdout, zap.DebugLevel)
	logger := zap.New(core, zap.AddCaller(), zap.AddCallerSkip(1))
	slog = logger.Sugar()
}

// InitLog 初始化日志
func InitLog(std bool, level string, cfgs ...Config) error {
	core, err := InitLogCore(std, level, cfgs...)
	if err != nil {
		return err
	}
	slog = core
	return nil
}

func InitLogCore(std bool, level string, cfgs ...Config) (*zap.SugaredLogger, error) {
	var cores []zapcore.Core
	if std {
		var stdLevel zapcore.Level
		if err := stdLevel.UnmarshalText([]byte(level)); err != nil {
			return nil, errors.New("unsupported std log level")
		}
		core := zapcore.NewCore(getEncoder(), os.Stderr, stdLevel)
		cores = append(cores, core)
	}
	for _, cfg := range cfgs {
		if !cfg.Enable {
			continue
		}
		core, err := getZapCore(cfg)
		if err != nil {
			return nil, err
		}
		cores = append(cores, core)
	}
	logger := zap.New(zapcore.NewTee(cores...), zap.AddCaller(), zap.AddCallerSkip(1))
	return logger.Sugar(), nil
}

func getZapCore(cfg Config) (zapcore.Core, error) {
	if cfg.Filename == "" {
		return nil, errors.New("empty log filename")
	}
	var level zapcore.Level
	if err := level.UnmarshalText([]byte(cfg.Level)); err != nil {
		return nil, errors.New("unsupported log level")
	}
	return zapcore.NewCore(getEncoder(), getLogWriter(cfg), zap.LevelEnablerFunc(func(l zapcore.Level) bool {
		switch cfg.LevelOp {
		case LevelLT:
			return l < level
		case LevelLE:
			return l <= level
		case LevelGE:
			return l >= level
		case LevelEQ:
			return l == level
		case LevelGT:
			return l > level
		default:
			return true
		}
	})), nil
}

func getEncoder() zapcore.Encoder {
	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	encoderConfig.EncodeLevel = zapcore.CapitalLevelEncoder
	return zapcore.NewJSONEncoder(encoderConfig)
}

func getLogWriter(cfg Config) zapcore.WriteSyncer {
	lumberJackLogger := &lumberjack.Logger{
		Filename:   cfg.Filename,
		MaxSize:    cfg.MaxSize,
		MaxBackups: cfg.MaxBackups,
		MaxAge:     cfg.MaxAge,
		Compress:   false,
	}
	return zapcore.AddSync(lumberJackLogger)
}

// Debugf debug日志
func Debugf(msg string, args ...interface{}) {
	slog.Debugf(msg, args...)
}

// Infof info日志
func Infof(msg string, args ...interface{}) {
	slog.Infof(msg, args...)
}

// Warnf Warn日志
func Warnf(msg string, args ...interface{}) {
	slog.Warnf(msg, args...)
}

// Errorf Error日志
func Errorf(msg string, args ...interface{}) {
	slog.Errorf(msg, args...)
}

// Panicf Panic日志
func Panicf(msg string, args ...interface{}) {
	slog.Panicf(msg, args...)
}

// Fatalf Fatal日志
func Fatalf(msg string, args ...interface{}) {
	slog.Fatalf(msg, args...)
}

func Log() *zap.SugaredLogger {
	return slog
}
