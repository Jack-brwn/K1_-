/**
 * ===========================================================================
 *  preprocess_rvv.c — RVV 加速图像预处理
 * ===========================================================================
 *  YOLO 预处理流水线: resize + normalize + HWC→CHW
 *  输入: uint8 BGR frame (H×W×3)
 *  输出: float32 blob (1×3×320×320)
 *
 *  编译: riscv64-unknown-linux-gnu-gcc -march=rv64gv -O3 -shared -fPIC
 *
 *  状态: 框架代码 (RVV intrinsics 待填充)
 * ===========================================================================
 */

#include <stdint.h>
#include <stddef.h>

/**
 * RVV 加速 resize + normalize + transpose
 *
 * @param src      输入帧 (uint8, H×W×3)
 * @param src_h    输入高度
 * @param src_w    输入宽度
 * @param dst      输出 blob (float32, 1×3×320×320) — 调用方分配
 * @param dst_h    目标高度 (320)
 * @param dst_w    目标宽度 (320)
 */
void preprocess_rvv(const uint8_t *src, int src_h, int src_w,
                    float *dst, int dst_h, int dst_w)
{
    // TODO: 使用 RVV intrinsics 实现:
    //   1. 双线性插值 resize (vle8.v, vse8.v)
    //   2. float32 归一化 (/255.0)
    //   3. HWC→CHW 转置 (vfadd.vf, vfmul.vf)
    //
    // 当前为 C 参考实现
    float scale_h = (float)src_h / dst_h;
    float scale_w = (float)src_w / dst_w;

    for (int c = 0; c < 3; c++) {
        for (int y = 0; y < dst_h; y++) {
            for (int x = 0; x < dst_w; x++) {
                int src_y = (int)(y * scale_h);
                int src_x = (int)(x * scale_w);
                if (src_y >= src_h) src_y = src_h - 1;
                if (src_x >= src_w) src_x = src_w - 1;

                uint8_t val = src[(src_y * src_w + src_x) * 3 + c];
                dst[c * dst_h * dst_w + y * dst_w + x] = val / 255.0f;
            }
        }
    }
}
