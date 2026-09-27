# tup=(1,2.0)
# print(all(isinstance(item, float ) for item in tup))
# all(isinstance(item, tuple) and len(item) == 2 or isinstance(item, float) for item in tup)
import random

# constant = 0.33  # 初始常数，您可以根据需要更改
# result = [i * constant if i * constant <1 else 1  for i in range(int(1 / constant) + 2)]

# # 确保开头和结尾是0和1
# # result[0] = 0
# # result[-1] = 1
# for i in range(0,3000):
#     if uni
# print(result)
import random

def find_index_above_random(random_num, values):
    return next((i for i, value in enumerate(values) if value > random_num), -1)

# 创建包含递增值的列表
constant = 0.1
values = [i * constant for i in range(int(1 / constant) + 1)]
values[0] = 0
values[-1] = 1

# 生成一个随机数
random_num = random.uniform(0, 1)
random_num =1
# 调用函数查找匹配的范围
index = find_index_above_random(random_num, values)

if index != -1:
    print(f"随机数 {random_num} 在列表中大于它的值的序号是 {index}")
else:
    print(f"随机数 {random_num} 不在列表的任何范围内")

