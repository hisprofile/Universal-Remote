# 1. Paste into a text block
# 2. Create a new bind and set to SCRIPT
# 3. Set text block as script to execute
obj = context.scene.camera
x, y, z = get_angvel_values(inputs)
q = obj.rotation_quaternion
q_delta = angvel_to_quat(x, -z, -y, 1/props.rate)
q = q @ q_delta
q.normalize()
obj.rotation_quaternion = q