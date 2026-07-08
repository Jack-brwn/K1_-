/**
 * ===========================================================================
 *  sensor_rvv.c — RVV 加速传感器信号处理
 * ===========================================================================
 *  向量化滑动窗口滤波、信号融合
 *  预留: 超声波/红外传感器数据流处理
 *
 *  编译: riscv64-unknown-linux-gnu-gcc -march=rv64gv -O3 -shared -fPIC
 *
 *  状态: 框架代码 (RVV intrinsics 待填充)
 * ===========================================================================
 */

#include <stdint.h>
#include <stddef.h>

/**
 * RVV 滑动窗口均值滤波
 *
 * @param data     输入信号 (float, N)
 * @param filtered 输出滤波结果 (float, N)
 * @param n        信号长度
 * @param win_size 窗口大小 (如 5)
 */
void moving_average_rvv(const float *data, float *filtered,
                        int n, int win_size)
{
    // TODO: RVV 向量化:
    //   使用滑动向量寄存器维护窗口和
    //   vfadd.vf / vfsub.vf 增量更新
    //
    // 当前为标量实现
    int half = win_size / 2;
    for (int i = 0; i < n; i++) {
        int start = i - half;
        if (start < 0) start = 0;
        int end = i + half + 1;
        if (end > n) end = n;

        float sum = 0.0f;
        int count = end - start;
        for (int j = start; j < end; j++) {
            sum += data[j];
        }
        filtered[i] = sum / count;
    }
}

/**
 * RVV 多传感器信号融合 (加权平均)
 *
 * @param signals 传感器数据 (float, channels × n), 行优先
 * @param weights 各通���权重 (float, channels)
 * @param fused   输出融合结果 (float, n)
 * @param channels 传感器通道数
 * @param n        每个通道的样本数
 */
void sensor_fusion_rvv(const float *signals, const float *weights,
                       float *fused, int channels, int n)
{
    // TODO: RVV 向量化:
    //   对每个时间点，向量化 channels 维度的加权求和
    //
    // 当前为标量实现
    for (int t = 0; t < n; t++) {
        float acc = 0.0f;
        for (int ch = 0; ch < channels; ch++) {
            acc += signals[ch * n + t] * weights[ch];
        }
        fused[t] = acc;
    }
}
