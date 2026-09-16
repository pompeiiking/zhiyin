package util

import (
	"strings"

	"github.com/spf13/viper"
)

func LoadConfig(in string, cfg interface{}) error {
	viper.SetConfigFile(in)
	viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_", "-", "_"))
	viper.AutomaticEnv()
	viper.AllowEmptyEnv(true)
	if err := viper.ReadInConfig(); err != nil {
		return err
	}

	return viper.Unmarshal(cfg)
}
