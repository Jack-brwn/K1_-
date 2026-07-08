/**
 * ===========================================================================
 *  verification_rvv.c — RVV 加速三级验证
 * ===========================================================================
 *  为 Python ThreeLevelVerify 提供加速函数:
 *    - highlight_count_rvv(): 高亮像素计数 (向量化阈值比较)
 *    - uniformity_rvv():      均匀度评分 (向量化方差)
 *
 *  编译: riscv64-unknown-linux-gnu-gcc -march=rv64gv -O3 -shared -fPIC
 *        -o libk1_rvv.so
 *
 *  Python ctypes 接口:
 *    highlight_count_rvv(ptr_uint8, total_pixels, threshold) → int
 *    uniformity_rvv(ptr_uint8, total_pixels) → float
 * ===========================================================================
 */

#include <stdint.h>
#include <stddef.h>
#include <math.h>

/**
 * 高亮像素计数 (RVV加速)
 *
 * @param data   灰度图数据 (uint8)
 * @param total  总像素数 (H×W)
 * @param thresh 阈值 (如 200)
 * @return       超过阈值的像素数
 */
int highlight_count_rvv(const uint8_t *data, int total, int thresh)
{
    // TODO: RVV 向量化:
    //   vsetvli t0, a1, e8, m8
    //   vle8.v v0, (a0)
    //   vmsgt.vx v1, v0, a2   # data[i] > thresh ?
    //   vcpop.m a0, v1        # popcount
    //
    // 当前为标量实现
    int count = 0;
    for (int i = 0; i < total; i++) {
        if (data[i] > (uint8_t)thresh) {
            count++;
        }
    }
    return count;
}

/**
 * 均匀度评分 (RVV加速)
 *
 * @param data  灰度图数据 (uint8)
 * @param total 总像素数
 * @return      均匀度 (1.0 = 完全均匀, < 0.7 = 可疑)
 */
float uniformity_rvv(const uint8_t *data, int total)
{
    // 计算均值
    float sum = 0.0f;
    for (int i = 0; i < total; i++) {
        sum += data[i];
    }
    float mean = sum / total;

    // 计算方差
    float var_sum = 0.0f;
    // TODO: RVV 向量化:
    //   vle8.v v0, (a0)
    //   vfwcvt.f.xu.v v2, v0       # 扩展 uint8 → float
    //   vfsub.vf v4, v2, fa0       # data[i] - mean
    //   vfmul.vv v6, v4, v4        # (data[i] - mean)^2
    //   vfredsum.vs fa0, v6, v0    # 归约求和
    //
    for (int i = 0; i < total; i++) {
        float diff = data[i] - mean;
        var_sum += diff * diff;
    }
    float variance = var_sum / total;

    // 归一化: var=0 → uni=1.0, var=10000 → uni=0.0
    float uni = 1.0f - (variance / 10000.0f);
    return uni < 0.0f ? 0.0f : (uni > 1.0f ? 1.0f : uni);
}
