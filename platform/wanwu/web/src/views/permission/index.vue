<template>
  <div class="page-wrapper" style="margin: 0 10px">
    <div class="page-title">
      <i class="el-icon-arrow-left" @click="$router.go(-1)" />
      <img class="page-title-img" src="@/assets/imgs/org.png" alt="" />
      <span class="page-title-name">{{$t('menu.setting')}}</span>
    </div>
    <div style="margin: 10px 20px 0 20px;">
      <div style="margin-bottom: -50px">
        <span
          v-for="item in list"
          :key="item.key"
          :class="['tab-span', {'is-active': radio === item.key}]"
          v-if="checkPerm(item.perm)"
          @click="changeTab(item.key)"
        >
          {{item.name}}
        </span>
      </div>
      <User v-if="radio === 'user'" />
      <Role v-if="radio === 'role'" />
      <Org v-if="radio === 'org'" />
    </div>
    <!--<router-view />-->
  </div>
</template>

<script>
import User from "./user/index.vue"
import Role from "./role/index.vue"
import Org from "./org/index.vue"
import { checkPerm, PERMS } from "@/router/permission"
import role from "@/views/permission/role/index.vue";

export default {
  components: {User, Role, Org},
  data() {
    return {
      radio: '',
      list: [
        {name: '用户', key: 'user', perm: PERMS.PERMISSION_USER},
        {name: '角色', key: 'role', perm: PERMS.PERMISSION_ROLE},
        {name: '组织', key: 'org', perm: PERMS.PERMISSION_ORG},
      ]
    }
  },
  created() {
    for (let item of this.list) {
      if (checkPerm(item.perm)) {
        this.radio = item.key
        break
      }
    }
  },
  methods: {
    checkPerm,
    changeTab(key) {
      this.radio = key
    }
  }
}
</script>

<style lang="scss" scoped>
.tab-span {
  display: inline-block;
  vertical-align: middle;
  padding: 6px 12px;
  border-radius: 6px;
  color: $color_title;
  cursor: pointer;
  margin-top: 10px;
}
.tab-span.is-active {
  color: $color;
  background: #fff;
  font-weight: bold;
}
.page-title {
  .el-icon-arrow-left {
    margin-right: 10px;
    font-size: 15px;
    cursor: pointer;
    color: $color_title;
  }
}
</style>
