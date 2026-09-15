<template>
  <div class="my_tools">
    <i class="el-icon-delete" @click="handleClick"></i>
  </div>
</template>
<script>
export default {
  inject: ["getNode"],
  data() {
    return {
      node: null,
    };
  },
  mounted() {
    this.node = this.getNode();
    this.node.on("click:data", ({ current }) => {
      alert(1);
    });
  },
  methods: {
    // handleClick() {
    //   this.node = this.getNode();
    //   //   this.
    // },
  },
};
</script>
<style lang="scss" scoped>
.my_tools {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  padding: 4px;
  cursor: pointer;
  border-radius: 3px;
  background: #fff;
  box-shadow: 0 1px 4px 3px #070c141f;
  gap: 4px;
}
</style>