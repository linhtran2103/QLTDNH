
document.addEventListener("DOMContentLoaded", async function () {

    // ==========================================
    // 1. CAU HINH CHUNG
    // ==========================================

    const currencyFormatter = new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND"
    });

    const TOKEN_KEY = "qltdnh_token";
    const USER_KEY = "qltdnh_user";

    let allFoods = [];
    let allCategories = [];

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function getUser() {
        try {
            return JSON.parse(localStorage.getItem(USER_KEY) || "null");
        } catch {
            return null;
        }
    }

    const isLoginPage = window.location.pathname.startsWith("/login");
    const isPublicOrderPage = window.location.pathname.startsWith("/order/");
    const currentPath = window.location.pathname;
    const currentRole = String(getUser()?.VaiTro || "").toLowerCase();

    const requiredRoles =
        currentPath === "/users"
            ? ["admin"]
            : currentPath === "/tables" ||
              currentPath === "/foods/add" ||
              currentPath.startsWith("/foods/edit/")
                ? ["admin", "manager"]
                : null;

    if (!isLoginPage && !isPublicOrderPage && !getToken()) {
        window.location.replace("/login");
        return;
    }

    if (requiredRoles && !requiredRoles.includes(currentRole)) {
        window.location.replace(currentRole ? "/" : "/login");
        return;
    }

    function getHeaders(json = true) {
        const headers = {};

        if (json) {
            headers["Content-Type"] = "application/json";
        }

        const token = getToken();

        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        return headers;
    }

    async function apiRequest(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...getHeaders(),
                ...(options.headers || {})
            }
        });

        let result;

        try {
            result = await response.json();
        } catch {
            throw new Error("Máy chủ trả về dữ liệu không hợp lệ.");
        }

        if (response.status === 401) {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);

            if (!window.location.pathname.includes("/login")) {
                alert("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
                window.location.href = "/login";
            }

            throw new Error(result.message || "Bạn cần đăng nhập lại.");
        }

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Có lỗi xảy ra.");
        }

        return result;
    }

    // Tải ảnh lên máy chủ
    async function uploadImage(file) {
        const formData = new FormData();
        formData.append("image", file);

        const response = await fetch("/api/upload-anh", {
            method: "POST",
            headers: {
                Authorization: `Bearer ${getToken()}`
            },
            body: formData
        });

        let result = {};

        try {
            result = await response.json();
        } catch {
            throw new Error("Máy chủ trả về dữ liệu không hợp lệ.");
        }

        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Không thể tải ảnh lên.");
        }

        return result.data.url;
    }

    function escapeHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;"
            }[char];
        });
    }

    function isActive(value) {
        return value === true || value === 1 || value === "1";
    }


    // ==========================================
    // 2. DANH SACH MON AN
    // ==========================================

    const foodTableBody = document.getElementById("foodTableBody");
    const foodSearch = document.getElementById("foodSearch");
    const categoryFilter = document.getElementById("categoryFilter");
    const statusFilter = document.getElementById("statusFilter");

    const totalFoods = document.getElementById("totalFoods");
    const availableFoods = document.getElementById("availableFoods");
    const unavailableFoods = document.getElementById("unavailableFoods");
    const totalCategories = document.getElementById("totalCategories");
    const resultCount = document.getElementById("resultCount");

    async function loadFoods() {
        if (!foodTableBody) return;

        try {
            const result = await apiRequest("/api/mon-an");

            allFoods = result.data || [];

            updateStatistics();
            loadCategoryFilter();
            filterFoods();

        } catch (error) {
            console.error("Lỗi tải món ăn:", error);

            foodTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger py-4">
                        ${escapeHTML(error.message)}
                    </td>
                </tr>
            `;
        }
    }

    function updateStatistics() {
        const available = allFoods.filter(food =>
            isActive(food.ConKinhDoanh)
        ).length;

        if (totalFoods) {
            totalFoods.textContent = allFoods.length;
        }

        if (availableFoods) {
            availableFoods.textContent = available;
        }

        if (unavailableFoods) {
            unavailableFoods.textContent = allFoods.length - available;
        }

        if (totalCategories) {
            totalCategories.textContent = allCategories.length;
        }
    }

    function loadCategoryFilter() {
        if (!categoryFilter) return;

        const selected = categoryFilter.value;

        categoryFilter.replaceChildren();

        const first = document.createElement("option");
        first.value = "";
        first.textContent = "Tất cả danh mục";
        categoryFilter.appendChild(first);

        allCategories.forEach(category => {
            const option = document.createElement("option");

            option.value = category.MaDanhMuc;
            option.textContent = category.TenDanhMuc;

            categoryFilter.appendChild(option);
        });

        categoryFilter.value = selected;
    }

    // ==========================================
    // HIỂN THỊ DANH SÁCH MÓN ĂN
    // ĐÃ BỔ SUNG NÚT XÓA
    // ==========================================

    function renderFoods(foods) {
        if (!foodTableBody) return;

        foodTableBody.replaceChildren();

        if (foods.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");

            cell.colSpan = 6;
            cell.className = "text-center py-4";
            cell.textContent = "Không tìm thấy món ăn phù hợp.";

            row.appendChild(cell);
            foodTableBody.appendChild(row);
        }

        foods.forEach(food => {
            const row = document.createElement("tr");

            const values = [
                food.MaMon || "",
                food.TenMonAn || "",
                food.TenDanhMuc || "",
                currencyFormatter.format(Number(food.Gia) || 0)
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            // Trạng thái món ăn
            const statusCell = document.createElement("td");
            const badge = document.createElement("span");

            const active = isActive(food.ConKinhDoanh);

            badge.className = active
                ? "badge bg-success"
                : "badge bg-danger";

            badge.textContent = active
                ? "Đang phục vụ"
                : "Ngừng phục vụ";

            statusCell.appendChild(badge);
            row.appendChild(statusCell);

            // Các nút thao tác
            const actionCell = document.createElement("td");

            const role = String(getUser()?.VaiTro || "").toLowerCase();

            if (["admin", "manager"].includes(role)) {

                // Nút sửa
                const editLink = document.createElement("a");

                editLink.href = `/foods/edit/${food.MaMonAn}`;
                editLink.className = "btn btn-sm btn-outline-primary me-1";
                editLink.textContent = "Sửa";

                actionCell.appendChild(editLink);

                // Nút xóa
                if (active) {
                    const deleteButton = document.createElement("button");

                    deleteButton.type = "button";
                    deleteButton.className = "btn btn-sm btn-outline-danger";
                    deleteButton.textContent = "Xóa";

                    deleteButton.addEventListener("click", async function () {

                        const confirmed = confirm(
                            `Bạn có chắc chắn muốn xóa món "${food.TenMonAn}" không?\n\nMón ăn sẽ được chuyển sang trạng thái ngừng kinh doanh.`
                        );

                        if (!confirmed) return;

                        try {
                            deleteButton.disabled = true;
                            deleteButton.textContent = "Đang xóa...";

                            await apiRequest(
                                `/api/mon-an/${food.MaMonAn}`,
                                {
                                    method: "DELETE"
                                }
                            );

                            alert("Đã xóa món ăn thành công!");

                            await loadFoods();

                        } catch (error) {
                            alert("Không thể xóa món ăn: " + error.message);

                            deleteButton.disabled = false;
                            deleteButton.textContent = "Xóa";
                        }
                    });

                    actionCell.appendChild(deleteButton);
                }
            }

            row.appendChild(actionCell);
            foodTableBody.appendChild(row);
        });

        if (resultCount) {
            resultCount.textContent =
                `Hiển thị ${foods.length} / ${allFoods.length} món ăn`;
        }
    }

    function filterFoods() {
        const keyword = foodSearch?.value.trim().toLowerCase() || "";
        const category = categoryFilter?.value || "";
        const status = statusFilter?.value || "";

        const filtered = allFoods.filter(food => {
            const name = (food.TenMonAn || "").toLowerCase();
            const code = (food.MaMon || "").toLowerCase();

            const matchesName =
                name.includes(keyword) || code.includes(keyword);

            const matchesCategory =
                !category || String(food.MaDanhMuc) === category;

            const active = isActive(food.ConKinhDoanh);

            const matchesStatus =
                !status ||
                (status === "available" && active) ||
                (status === "unavailable" && !active);

            return matchesName && matchesCategory && matchesStatus;
        });

        renderFoods(filtered);
    }

    foodSearch?.addEventListener("input", filterFoods);
    categoryFilter?.addEventListener("change", filterFoods);
    statusFilter?.addEventListener("change", filterFoods);


    // ==========================================
    // 3. DANH MUC MON AN
    // ==========================================

    async function fetchCategories() {
        try {
            const result = await apiRequest(
                "/api/danh-muc?trang_thai=true"
            );

            allCategories = result.data || [];

            updateStatistics();
            loadCategoryFilter();

            const addCategory = document.getElementById("foodCategory");
            const editForm = document.getElementById("editFoodForm");

            if (addCategory && !editForm) {
                loadCategories(addCategory);
            }

        } catch (error) {
            console.error("Lỗi tải danh mục:", error);
        }
    }

    function loadCategories(selectElement, selectedId = "") {
        if (!selectElement) return;

        selectElement.replaceChildren();

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Chọn danh mục";
        selectElement.appendChild(placeholder);

        allCategories.forEach(category => {
            const option = document.createElement("option");

            option.value = category.MaDanhMuc;
            option.textContent = category.TenDanhMuc;

            selectElement.appendChild(option);
        });

        if (selectedId !== "") {
            selectElement.value = String(selectedId);
        }
    }


    // ==========================================
    // 4. XEM TRUOC ANH MON AN
    // ==========================================

    function setupImagePreview(inputId, previewId, removeId) {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        const removeButton = document.getElementById(removeId);

        if (!input || !preview) return;

        let currentObjectURL = null;

        const placeholder = preview.parentElement?.querySelector(
            ".image-preview-placeholder"
        );

        input.addEventListener("change", function () {
            const file = input.files?.[0];

            if (!file) return;

            const allowedTypes = [
                "image/jpeg",
                "image/png",
                "image/webp"
            ];

            if (!allowedTypes.includes(file.type)) {
                alert("Vui lòng chọn ảnh JPG, PNG hoặc WEBP.");

                input.value = "";
                return;
            }

            if (file.size > 5 * 1024 * 1024) {
                alert("Ảnh không được vượt quá 5MB.");

                input.value = "";
                return;
            }

            if (currentObjectURL) {
                URL.revokeObjectURL(currentObjectURL);
            }

            currentObjectURL = URL.createObjectURL(file);

            preview.src = currentObjectURL;
            preview.style.display = "block";

            if (removeButton) {
                removeButton.hidden = false;
                removeButton.style.display = "";
            }

            if (placeholder) {
                placeholder.style.display = "none";
            }
        });

        removeButton?.addEventListener("click", function () {
            input.value = "";

            if (currentObjectURL) {
                URL.revokeObjectURL(currentObjectURL);
                currentObjectURL = null;
            }

            preview.removeAttribute("src");
            preview.style.display = "none";

            if (removeButton) {
                removeButton.hidden = true;
                removeButton.style.display = "none";
            }

            if (placeholder) {
                placeholder.style.display = "flex";
            }
        });
    }

    setupImagePreview(
        "foodImage",
        "imagePreview",
        "removeImage"
    );

    setupImagePreview(
        "editFoodImage",
        "editImagePreview",
        "removeEditImage"
    );


    // ==========================================
    // 5. THEM MON AN
    // ==========================================

    const addFoodForm = document.getElementById("addFoodForm");

    addFoodForm?.addEventListener("submit", async function (event) {
        event.preventDefault();

        const code = document.getElementById("foodCode")?.value.trim();
        const name = document.getElementById("foodName")?.value.trim();
        const category = document.getElementById("foodCategory")?.value;

        const price = Number(
            document.getElementById("foodPrice")?.value
        );

        const description =
            document.getElementById("foodDescription")?.value.trim() || "";

        const saveButton = document.getElementById("saveFoodButton");

        if (!code || !name || !category || !price || price <= 0) {
            alert("Vui lòng nhập đầy đủ thông tin món ăn hợp lệ.");
            return;
        }

        if (!getToken()) {
            alert("Vui lòng đăng nhập trước khi thêm món ăn.");
            window.location.href = "/login";
            return;
        }

        const payload = {
            MaMon: code,
            TenMonAn: name,
            MaDanhMuc: Number(category),
            Gia: price,
            MoTa: description,
            HinhAnh: null
        };

        try {
            if (saveButton) {
                saveButton.disabled = true;
                saveButton.textContent = "Đang lưu...";
            }

            const imageFile =
                document.getElementById("foodImage")?.files?.[0];

            if (imageFile) {
                payload.HinhAnh = await uploadImage(imageFile);
            }

            await apiRequest("/api/mon-an", {
                method: "POST",
                body: JSON.stringify(payload)
            });

            alert("Thêm món ăn thành công!");
            window.location.href = "/foods";

        } catch (error) {
            alert("Không thể thêm món ăn: " + error.message);

        } finally {
            if (saveButton) {
                saveButton.disabled = false;
                saveButton.textContent = "Lưu món ăn";
            }
        }
    });


    // ==========================================
    // 6. SUA MON AN
    // ==========================================

    const editFoodForm = document.getElementById("editFoodForm");

    if (editFoodForm) {
        const pathParts = window.location.pathname.split("/");
        const foodId = decodeURIComponent(pathParts[pathParts.length - 1]);

        let currentImageURL = "";

        async function loadFoodForEdit() {
            try {
                const [foodResult] = await Promise.all([
                    apiRequest(`/api/mon-an/${foodId}`),
                    fetchCategories()
                ]);

                const food = foodResult.data;

                if (!food) {
                    alert("Không tìm thấy món ăn.");
                    window.location.href = "/foods";
                    return;
                }

                document.getElementById("foodCode").value =
                    food.MaMon || "";

                document.getElementById("foodName").value =
                    food.TenMonAn || "";

                document.getElementById("foodPrice").value =
                    food.Gia || "";

                document.getElementById("foodDescription").value =
                    food.MoTa || "";

                loadCategories(
                    document.getElementById("foodCategory"),
                    food.MaDanhMuc
                );

                const statusInput = document.getElementById("foodStatus");

                if (statusInput) {
                    statusInput.value = isActive(food.ConKinhDoanh)
                        ? "1"
                        : "0";
                }

                currentImageURL = food.HinhAnh || "";

                const preview = document.getElementById("editImagePreview");

                if (preview && currentImageURL) {
                    preview.src = currentImageURL;
                    preview.style.display = "block";

                    const placeholder = preview.parentElement?.querySelector(
                        ".image-preview-placeholder"
                    );

                    if (placeholder) {
                        placeholder.style.display = "none";
                    }
                }

            } catch (error) {
                console.error("Lỗi tải món ăn:", error);
                alert("Không thể tải thông tin món ăn: " + error.message);
            }
        }

        editFoodForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const name = document.getElementById("foodName")?.value.trim();
            const category = document.getElementById("foodCategory")?.value;

            const price = Number(
                document.getElementById("foodPrice")?.value
            );

            const description =
                document.getElementById("foodDescription")?.value.trim() || "";

            if (!name || !category || !price || price <= 0) {
                alert("Vui lòng nhập đầy đủ thông tin hợp lệ.");
                return;
            }

            const payload = {
                TenMonAn: name,
                MaDanhMuc: Number(category),
                Gia: price,
                MoTa: description,
                HinhAnh: currentImageURL,
                ConKinhDoanh:
                    document.getElementById("foodStatus")?.value ?? "1"
            };

            try {
                const imageFile =
                    document.getElementById("editFoodImage")?.files?.[0];

                if (imageFile) {
                    payload.HinhAnh = await uploadImage(imageFile);
                }

                await apiRequest(`/api/mon-an/${foodId}`, {
                    method: "PUT",
                    body: JSON.stringify(payload)
                });

                alert("Cập nhật món ăn thành công!");
                window.location.href = "/foods";

            } catch (error) {
                alert("Không thể cập nhật món ăn: " + error.message);
            }
        });

        loadFoodForEdit();
    }


    // ==========================================
    // 7. DANG NHAP
    // ==========================================

    const loginForm = document.getElementById("loginForm");

    loginForm?.addEventListener("submit", async function (event) {
        event.preventDefault();

        const username =
            document.getElementById("username")?.value.trim() ||
            document.getElementById("TenDangNhap")?.value.trim();

        const password =
            document.getElementById("password")?.value ||
            document.getElementById("MatKhau")?.value;

        const loginMessage = document.getElementById("loginMessage");

        const submitButton = loginForm.querySelector(
            'button[type="submit"]'
        );

        if (!username || !password) {
            if (loginMessage) {
                loginMessage.textContent =
                    "Vui lòng nhập tên đăng nhập và mật khẩu.";
            } else {
                alert("Vui lòng nhập tên đăng nhập và mật khẩu.");
            }

            return;
        }

        try {
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = "Đang đăng nhập...";
            }

            const response = await fetch("/api/dang-nhap", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    TenDangNhap: username,
                    MatKhau: password
                })
            });

            const result = await response.json();

            if (!response.ok || result.status !== "success") {
                throw new Error(
                    result.message || "Tên đăng nhập hoặc mật khẩu không đúng."
                );
            }

            if (!result.token) {
                throw new Error("Máy chủ không trả về mã đăng nhập.");
            }

            localStorage.setItem(TOKEN_KEY, result.token);

            localStorage.setItem(
                USER_KEY,
                JSON.stringify(result.data || {})
            );

            window.location.href = "/";

        } catch (error) {
            if (loginMessage) {
                loginMessage.textContent = error.message;
            } else {
                alert(error.message);
            }

        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = "Đăng nhập";
            }
        }
    });


    // ==========================================
    // 8. DANG XUAT
    // ==========================================

    document.querySelectorAll("[data-logout]").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();

            const confirmed = confirm("Bạn có chắc chắn muốn đăng xuất?");

            if (!confirmed) return;

            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);

            window.location.href = "/login";
        });
    });


    // ==========================================
    // 9. HIEN THI THONG TIN NGUOI DUNG
    // ==========================================

    const currentUser = getUser();

    const roleLabels = {
        admin: "Admin",
        manager: "Quản lý",
        nhanvien: "Nhân viên",
        user: "Nhân viên"
    };

    document.querySelectorAll("[data-roles]").forEach(element => {
        const allowed = element.dataset.roles
            .split(",")
            .map(value => value.trim());

        const role = String(currentUser?.VaiTro || "").toLowerCase();

        if (!allowed.some(value => value.toLowerCase() === role)) {
            element.hidden = true;
        }
    });

    document.querySelectorAll("[data-user-name]").forEach(element => {
        element.textContent =
            currentUser?.HoTen ||
            currentUser?.TenDangNhap ||
            "Người dùng";
    });

    document.querySelectorAll("[data-user-role]").forEach(element => {
        const role = String(currentUser?.VaiTro || "").toLowerCase();
        element.textContent = roleLabels[role] || "Nhân viên";
    });


    // ==========================================
    // 10. THONG BAO CHUC NANG CHUA HO TRO
    // ==========================================

    document.querySelectorAll("[data-coming-soon]").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            alert("Chức năng này đang được phát triển.");
        });
    });


    // ==========================================
    // 11. TAI THONG KE DASHBOARD
    // ==========================================

    const dashboardPage =
        document.getElementById("totalFoods") &&
        !foodTableBody;

    async function loadDashboardStats() {
        if (!dashboardPage) return;

        try {
            const [foodResult, categoryResult] = await Promise.all([
                apiRequest("/api/mon-an"),
                apiRequest("/api/danh-muc?trang_thai=true")
            ]);

            allFoods = foodResult.data || [];
            allCategories = categoryResult.data || [];

            updateStatistics();

        } catch (error) {
            console.error(
                "Lỗi tải thống kê Dashboard:",
                error
            );
        }
    }


    // ==========================================
    // 12. KHOI TAO DU LIEU THEO TUNG TRANG
    // ==========================================

    const hasCategorySelect =
        document.getElementById("foodCategory");

    if (foodTableBody || hasCategorySelect || editFoodForm) {
        await fetchCategories();
    }

    if (foodTableBody) {
        await loadFoods();
    }

    if (dashboardPage) {
        await loadDashboardStats();
    }

});
