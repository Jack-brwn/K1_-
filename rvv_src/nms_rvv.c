/**
 * ===========================================================================
 *  nms_rvv.c — RVV 加速 Non-Maximum Suppression
 * ===========================================================================
 *  向量化 IoU 计算，加速框去重。
 *  输入: boxes (N×4), scores (N)
 *  输出: keep 索引数组
 *
 *  编译: riscv64-unknown-linux-gnu-gcc -march=rv64gv -O3 -shared -fPIC
 *
 *  状态: 框架代码 (RVV intrinsics 待填充)
 * ===========================================================================
 */

#include <stdint.h>
#include <stddef.h>

/**
 * RVV 加速 NMS (向量化 IoU)
 *
 * @param boxes    边界框数组 [x1,y1,x2,y2] (float, N×4)
 * @param scores   置信度数组 (float, N)
 * @param n        边界框数量
 * @param iou_thr  IoU 阈值 (如 0.45)
 * @param keep     输出: 保留的索引数组 (int, 调用方分配，最多 N)
 * @return         保留的框数
 */
int nms_rvv(const float *boxes, const float *scores, int n,
            float iou_thr, int *keep)
{
    // TODO: 使用 RVV intrinsics 向量化内层 IoU 循环:
    //   area_i = (x2_i - x1_i) * (y2_i - y1_i)
    //   inter_w = min(x2_i, x2_j) - max(x1_i, x1_j)  (clip to 0)
    //   inter_h = min(y2_i, y2_j) - max(y1_i, y1_j)  (clip to 0)
    //   inter = inter_w * inter_h
    //   iou = inter / (area_i + area_j - inter)
    //
    // 当前为 C 参考实现 (贪心算法)
    int *suppressed = (int *)__builtin_alloca(n * sizeof(int));
    for (int i = 0; i < n; i++) suppressed[i] = 0;

    int count = 0;
    for (int i = 0; i < n; i++) {
        if (suppressed[i]) continue;
        keep[count++] = i;

        float x1_i = boxes[i * 4 + 0];
        float y1_i = boxes[i * 4 + 1];
        float x2_i = boxes[i * 4 + 2];
        float y2_i = boxes[i * 4 + 3];
        float area_i = (x2_i - x1_i) * (y2_i - y1_i);

        for (int j = i + 1; j < n; j++) {
            if (suppressed[j]) continue;

            float x1_j = boxes[j * 4 + 0];
            float y1_j = boxes[j * 4 + 1];
            float x2_j = boxes[j * 4 + 2];
            float y2_j = boxes[j * 4 + 3];
            float area_j = (x2_j - x1_j) * (y2_j - y1_j);

            float inter_w = (x2_i < x2_j ? x2_i : x2_j) -
                            (x1_i > x1_j ? x1_i : x1_j);
            float inter_h = (y2_i < y2_j ? y2_i : y2_j) -
                            (y1_i > y1_j ? y1_i : y1_j);
            if (inter_w <= 0 || inter_h <= 0) continue;

            float inter = inter_w * inter_h;
            float iou = inter / (area_i + area_j - inter);

            if (iou > iou_thr) {
                if (scores[i] >= scores[j]) {
                    suppressed[j] = 1;
                } else {
                    suppressed[i] = 1;
                    count--;
                    break;
                }
            }
        }
    }
    return count;
}
